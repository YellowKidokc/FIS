from __future__ import annotations
import json
import mimetypes
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from core.models import ActionPlan, ActionStep, DecisionRecord, ReviewBlock, to_dict
from core.orchestrator import run_folder_intelligence
from core.action_plans import create_plan, approve_plan, DISABLED_OPERATIONS, ALLOWED_OPERATIONS
from core.executor import preview_plan, execute_plan
from core.safety import check_plan
from core.runtime_store import runtime_store
from core.recipes import build_recipe_candidates, to_dict as recipe_to_dict
from core.storyboards import build_storyboard, to_dict as storyboard_to_dict

_LAST = {"plans": {}, "blocks": {}, "results": {}, "decisions": [], "storyboards": {}, "executor_logs": []}
_LOCK = threading.Lock()
_SCAN_JOBS: dict[str, dict] = {}
_SCAN_JOB_SEQ = 0

ROUTES = {
    "GET": ["/", "/api/health", "/api/routes", "/api/cache/status", "/api/stats", "/api/scan", "/api/scan/status", "/api/folderbrain", "/api/review/blocks", "/api/review/block", "/api/findings", "/api/recipes", "/api/recipes/next", "/api/storyboard", "/api/preferences/stats"],
    "POST": ["/api/scan", "/api/storyboard/build", "/api/storyboard/decision", "/api/action/plan", "/api/action/preview", "/api/action/approve", "/api/action/execute", "/api/preferences/record", "/api/project/export-prompt"],
}


def _new_scan_job(path: str) -> dict:
    global _SCAN_JOB_SEQ
    with _LOCK:
        _SCAN_JOB_SEQ += 1
        job_id = f"scan_{_SCAN_JOB_SEQ:05d}"
        job = {
            "job_id": job_id,
            "path": path,
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "current_stage": "queued",
            "current_label": "Queued",
            "current": 0,
            "total": 0,
            "events": [],
            "result": None,
            "error": None,
        }
        _SCAN_JOBS[job_id] = job
        return dict(job)


def _update_scan_job(job_id: str, **updates):
    with _LOCK:
        job = _SCAN_JOBS.get(job_id)
        if not job:
            return
        job.update(updates)
        job["updated_at"] = time.time()


def _append_scan_event(job_id: str, event: dict):
    with _LOCK:
        job = _SCAN_JOBS.get(job_id)
        if not job:
            return
        event = dict(event)
        event["at"] = time.time()
        job["events"].append(event)
        job["current_stage"] = event.get("stage", job["current_stage"])
        job["current_label"] = event.get("label", job["current_label"])
        job["current"] = event.get("current", job["current"])
        job["total"] = event.get("total", job["total"])
        job["status"] = "running"
        job["updated_at"] = time.time()


def _scan_job_snapshot(job_id: str) -> dict | None:
    with _LOCK:
        job = _SCAN_JOBS.get(job_id)
        return dict(job) if job else None


def _run_scan_job(job_id: str, path: str, options=None):
    _update_scan_job(job_id, status="running", current_stage="starting", current_label="Starting scan")
    try:
        result = run_folder_intelligence(path, options, progress_callback=lambda event: _append_scan_event(job_id, event))
        if result.get("error"):
            _update_scan_job(job_id, status="error", error=result["error"], result=result)
            return
        with _LOCK:
            _LAST["results"][path] = result
            for block in result["review_blocks"]:
                _LAST["blocks"][block["block_id"]] = block
        _update_scan_job(job_id, status="complete", result=result, current_stage="complete", current_label="Scan complete")
    except Exception as exc:
        _update_scan_job(job_id, status="error", error=str(exc))

def envelope(data=None, warnings=None, errors=None, ok=None):
    errs = errors or []
    if isinstance(errs, str): errs = [errs]
    payload = {"ok": (not errs if ok is None else ok), "data": data or {}, "warnings": warnings or [], "errors": errs}
    if isinstance(data, dict):
        payload.update({k: v for k, v in data.items() if k not in payload})
    return payload

def _send(handler, payload, status=200, raw=False):
    if not raw and not (isinstance(payload, dict) and set(payload.keys()) >= {"ok", "data", "warnings", "errors"}):
        if isinstance(payload, dict) and (payload.get("error") or payload.get("errors")):
            err = payload.get("error") or payload.get("errors")
            errs = err if isinstance(err, list) else [err]
            payload = envelope(errors=errs, ok=False)
        else:
            payload = envelope(payload)
    data = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

_MAX_STATIC_SIZE = 10 * 1024 * 1024  # 10 MB

def _send_file(handler, path: Path):
    if path.stat().st_size > _MAX_STATIC_SIZE:
        _send(handler, {"error": "file too large"}, 413)
        return
    data = path.read_bytes()
    ct, _ = mimetypes.guess_type(str(path))
    if ct is None:
        ct = "text/html; charset=utf-8" if path.suffix == ".html" else "application/octet-stream"
    handler.send_response(200)
    handler.send_header("Content-Type", ct)
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def _block_from_store(block_id: str) -> ReviewBlock | None:
    with _LOCK:
        data = _LAST["blocks"].get(block_id)
    return ReviewBlock(**data) if data else None

def _plan_from_dict(data: dict) -> ActionPlan:
    return ActionPlan(data["plan_id"], data["source_block_id"], data["dry_run"], data["approved"], [ActionStep(**s) for s in data.get("steps", [])], data.get("created_by", "river"), data.get("metadata", {}))

def _recipes_for(path: str) -> list[dict]:
    with _LOCK:
        result = _LAST["results"].get(path)
    if result is None:
        result = run_folder_intelligence(path)
    if not result.get("error"):
        with _LOCK:
            _LAST["results"][path] = result
            for block in result.get("review_blocks", []):
                _LAST["blocks"][block["block_id"]] = block
    recipes = []
    for block in result.get("review_blocks", []):
        suggested = block.get("suggested_actions") or []
        action = next((a for a in suggested if a in ALLOWED_OPERATIONS), None)
        if action is None:
            continue
        recipes.append({
            "recipe_id": f"recipe_{block['block_id']}",
            "block_id": block["block_id"],
            "title": block.get("title", "Review"),
            "summary": block.get("summary") or "River found something worth reviewing before action.",
            "why": f"Based on {len(block.get('metadata', {}).get('finding_ids', []))} finding(s) and {block.get('item_count', 0)} affected item(s).",
            "confidence": block.get("confidence", 0),
            "risk": block.get("risk", "low"),
            "affected_count": block.get("item_count", 0),
            "evidence_count": len(block.get("metadata", {}).get("finding_ids", [])),
            "action": action,
        })
    return sorted(recipes, key=lambda r: (r["risk"] != "low", -r["confidence"], -r["affected_count"]))

def _storyboard(recipe: dict, path: str) -> dict:
    required_keys = {"recipe_id", "title", "summary"}
    missing = required_keys - recipe.keys()
    if missing:
        raise KeyError(f"recipe missing required keys: {missing}")
    sid = f"story_{recipe['recipe_id']}"
    story = {
        "storyboard_id": sid, "recipe": recipe, "path": path,
        "title": recipe["title"],
        "headline": "Nothing will be changed until you approve and explicitly execute.",
        "progress": ["Found", "Preview", "Safety", "Approve", "Execute", "Record"],
        "found": recipe.get("summary", ""),
        "wants_to_do": "River will prepare a dry-run plan first, then show safety blockers in plain language.",
        "will_change": [],
        "will_not_touch": ["Protected folders", "Database files", "System folders", "Unknown risky items", "Deletes"],
        "safety": {"status": "preview_required", "blockers": ["No plan preview has been approved yet"]},
        "plan_id": None,
    }
    with _LOCK:
        _LAST["storyboards"][sid] = story
    return story

class RiverHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    def do_OPTIONS(self): _send(self, envelope({"options": True}))
    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length: return {}
        try: return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON: {exc}")
    def _path_from(self, qs, body=None): return (body or {}).get("path") or qs.get("path", qs.get("root", [""]))[0]
    def _scan(self, path: str, options=None):
        result = run_folder_intelligence(path, options)
        if not result.get("error"):
            with _LOCK:
                _LAST["results"][path] = result
                for block in result["review_blocks"]:
                    _LAST["blocks"][block["block_id"]] = block
        return result
    def _run(self, path: str, options=None):
        with _LOCK:
            cached = _LAST["results"].get(path)
        if cached is not None and options in (None, {}):
            return cached
        return self._scan(path, options)
    def do_GET(self):
        parsed = urlparse(self.path); qs = parse_qs(parsed.query); path = self._path_from(qs)
        if parsed.path == "/": return _send_file(self, Path(__file__).resolve().parents[1] / "ui" / "index.html")
        if parsed.path.startswith("/ui/"):
            target = (Path(__file__).resolve().parents[1] / parsed.path.lstrip("/")).resolve()
            root = (Path(__file__).resolve().parents[1] / "ui").resolve()
            try:
                target.relative_to(root)
            except ValueError:
                return _send(self, {"error": "forbidden"}, 403)
            if target.exists():
                ct, _ = mimetypes.guess_type(str(target))
                if ct is None:
                    ct = "text/plain"
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return
        if parsed.path == "/api/health": return _send(self, {"service": "River FIS", "guided": True, "status": "ok"})
        if parsed.path == "/api/routes": return _send(self, {"routes": ROUTES})
        if parsed.path == "/api/scan/status":
            job_id = qs.get("id", [""])[0]
            job = _scan_job_snapshot(job_id)
            return _send(self, job if job else {"error": "scan job not found"}, 200 if job else 404)
        if parsed.path == "/api/preferences/stats":
            with _LOCK:
                dec_len = len(_LAST["decisions"])
            return _send(self, {"events": dec_len, "learning_enabled": True, "preview_only": True})
        if parsed.path in {"/api/cache/status", "/api/stats"}:
            with _LOCK:
                snap = {k: len(v) if isinstance(v, (dict, list)) else v for k, v in _LAST.items()}
            return _send(self, {**snap, "allowed_operations": sorted(ALLOWED_OPERATIONS), "blocked_operations": sorted(DISABLED_OPERATIONS), "executor_status": "idle", "cache_status": "memory"})
        if parsed.path in {"/api/folderbrain", "/api/cache/folderbrain"}:
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, self._run(path).get("folderbrain"))
        if parsed.path in {"/api/review/blocks", "/api/findings", "/api/cache/findings"}:
            if not path: return _send(self, {"error": "path/root is required"}, 400)
            result = self._run(path); return _send(self, {"blocks": result.get("review_blocks", []), "findings": result.get("findings", []), "warnings": result.get("warnings", [])})
        if parsed.path == "/api/review/block":
            block_id = qs.get("id", [""])[0]
            with _LOCK:
                exists = block_id in _LAST["blocks"]
                val = _LAST["blocks"].get(block_id, {"error": "block not found"})
            return _send(self, val, 200 if exists else 404)
        if parsed.path in {"/api/scan", "/api/cache/scan"}:
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, self._run(path))
        if parsed.path == "/api/recipes":
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, {"recipes": _recipes_for(path)})
        if parsed.path == "/api/recipes/next":
            if not path: return _send(self, {"error": "path is required"}, 400)
            recipes = _recipes_for(path); return _send(self, {"recipe": recipes[0] if recipes else None, "secondary": recipes[1:4]})
        if parsed.path == "/api/storyboard":
            sid = qs.get("id", [""])[0]
            with _LOCK:
                exists = sid in _LAST["storyboards"]
                val = _LAST["storyboards"].get(sid, {"error": "storyboard not found"})
            return _send(self, val, 200 if exists else 404)
        if parsed.path in {"/api/actions", "/api/roots"}: return _send(self, {"status": "compatibility_wrapper", "preview_only": True})
        return _send(self, {"error": "not found"}, 404)
    def do_POST(self):
        parsed = urlparse(self.path); body = self._body(); qs = parse_qs(parsed.query); path = self._path_from(qs, body)
        if parsed.path == "/api/scan":
            if not path: return _send(self, {"error": "path is required"}, 400)
            if body.get("async"):
                job = _new_scan_job(path)
                worker = threading.Thread(target=_run_scan_job, args=(job["job_id"], path, body.get("options")), daemon=True)
                worker.start()
                return _send(self, {"job_id": job["job_id"], "status": "queued", "path": path})
            return _send(self, self._run(path, body.get("options")))
        if parsed.path == "/api/storyboard/build":
            recipe = body.get("recipe") or next((r for r in _recipes_for(path) if r["recipe_id"] == body.get("recipe_id")), None)
            if not recipe: return _send(self, {"error": "recipe not found"}, 404)
            try:
                return _send(self, _storyboard(recipe, path))
            except KeyError as e:
                return _send(self, {"error": str(e)}, 400)
        if parsed.path in {"/api/storyboard/decision", "/api/preferences/record", "/api/review/decide"}:
            with _LOCK:
                _LAST["decisions"].append(body)
            return _send(self, {"recorded": True, "decision": body, "preview_only": True})
        if parsed.path == "/api/action/plan":
            block = _block_from_store(body.get("block_id", "")) or (ReviewBlock(**body["block"]) if body.get("block") else None)
            if not block: return _send(self, {"error": "block not found; run /api/scan or pass block"}, 404)
            decision = DecisionRecord("api", block.block_id, body.get("action", "review"), "approved", body.get("note", ""))
            plan = create_plan(block, decision, action=body.get("action"), folder_path=path, payload=body)
            with _LOCK:
                _LAST["plans"][plan.plan_id] = plan
            return _send(self, to_dict(plan))
        if parsed.path == "/api/action/preview":
            plan = _plan_from_dict(body["plan"]) if body.get("plan") else _LAST["plans"].get(body.get("plan_id")); return _send(self, preview_plan(plan) if plan else {"error": "plan not found"}, 200 if plan else 404)
        if parsed.path == "/api/action/approve":
            with _LOCK:
                plan = _LAST["plans"].get(body.get("plan_id"))
            if not plan: return _send(self, {"error": "plan not found"}, 404)
            plan = approve_plan(plan, bool(body.get("approved", True)))
            with _LOCK:
                _LAST["plans"][plan.plan_id] = plan
            return _send(self, {"plan": to_dict(plan), "safety": to_dict(check_plan(plan))})
        if parsed.path == "/api/action/execute":
            if not body.get("confirm_execute"): return _send(self, {"error": "confirm_execute=true is required"}, 400)
            with _LOCK:
                plan = _LAST["plans"].get(body.get("plan_id"))
            if not plan:
                return _send(self, {"error": "plan not found"}, 404)
            result = execute_plan(plan)
            if result.get("error"):
                return _send(self, result, 500)
            with _LOCK:
                _LAST["executor_logs"].append(result)
            return _send(self, result, 200)
        if parsed.path == "/api/project/export-prompt":
            from scripts.export_project_prompt import export_project_prompt
            return _send(self, export_project_prompt(body.get("root", "."), body.get("output", "FIS_PROJECT_CONTEXT.md")))
        return _send(self, {"error": "not found"}, 404)

def run(host="127.0.0.1", port=61845):
    print(f"River FIS running at http://{host}:{port}/")
    ThreadingHTTPServer((host, port), RiverHandler).serve_forever()
if __name__ == "__main__": run()
