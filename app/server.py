from __future__ import annotations
import json, mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlparse
from core.models import ActionPlan, ActionStep, DecisionRecord, ReviewBlock, to_dict
from core.orchestrator import run_folder_intelligence
from core.action_plans import create_plan, approve_plan, executable_copy
from core.executor import preview_plan, execute_plan
from core.safety import check_plan
from core.runtime_store import runtime_store

ROOT = Path(__file__).resolve().parents[1]
UI_DIR = ROOT / "ui"
API_PREFIX = "/api/"

def envelope(data=None, ok: bool = True, warnings=None, errors=None):
    return {"ok": ok, "data": data, "warnings": warnings or [], "errors": errors or []}

def _send_json(handler, payload, status=200):
    if not (isinstance(payload, dict) and {"ok", "data", "warnings", "errors"}.issubset(payload.keys())):
        payload = envelope(payload)
    data = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers(); handler.wfile.write(data)

def _send_file(handler, path: Path):
    data = path.read_bytes(); ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    handler.send_response(200); handler.send_header("Content-Type", ctype); handler.send_header("Content-Length", str(len(data))); handler.end_headers(); handler.wfile.write(data)

def _plan_from_dict(data: dict) -> ActionPlan:
    return ActionPlan(data["plan_id"], data["source_block_id"], data["dry_run"], data["approved"], [ActionStep(**s) for s in data.get("steps", [])], data.get("created_by", "river"), data.get("metadata", {}))

def _decision_from_body(body: dict) -> DecisionRecord:
    return DecisionRecord(body.get("decision_id", f"decision_{len(runtime_store.decisions)+1:05d}"), body.get("block_id", ""), body.get("action", "review"), body.get("decision", "pending"), body.get("note", ""), body)

class RiverHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    def do_OPTIONS(self): _send_json(self, envelope({"ok": True}))
    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        if not length: return {}
        try: return json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc: raise ValueError(f"Invalid JSON: {exc}")
    def _path_from(self, qs, body=None): return (body or {}).get("path") or qs.get("path", qs.get("root", [""]))[0]
    def _scan(self, path: str, options=None):
        result = run_folder_intelligence(path, options)
        if result.get("error"):
            return envelope(None, False, result.get("warnings", []), [result["error"]])
        runtime_store.put_scan(path, result)
        return envelope(result, True, result.get("warnings", []), [])
    def _serve_static(self, parsed):
        req = unquote(parsed.path)
        if req in {"/", ""}: target = UI_DIR / "index.html"
        else:
            rel = req.lstrip("/")
            target = (UI_DIR / rel).resolve() if not rel.startswith("ui/") else (ROOT / rel).resolve()
            if UI_DIR not in target.parents and target != UI_DIR / "index.html":
                return False
        if target.exists() and target.is_file(): _send_file(self, target); return True
        return False
    def do_GET(self):
        parsed = urlparse(self.path); qs = parse_qs(parsed.query); path = self._path_from(qs)
        try:
            if not parsed.path.startswith(API_PREFIX):
                if self._serve_static(parsed): return
                return _send_json(self, envelope(None, False, [], ["static file not found"]), 404)
            if parsed.path == "/api/health": return _send_json(self, envelope({"service": "River FIS", "host": self.server.server_address[0], "port": self.server.server_address[1], "ui": "/", "api_base": "/api"}))
            if parsed.path in {"/api/cache/status", "/api/stats", "/api/preferences/stats"}: return _send_json(self, envelope(runtime_store.status()))
            if parsed.path in {"/api/folderbrain", "/api/cache/folderbrain"}:
                if not path: return _send_json(self, envelope(None, False, [], ["path is required"]), 400)
                cached = runtime_store.get_scan(path) or self._scan(path)["data"]
                return _send_json(self, envelope(cached.get("folderbrain"), True, cached.get("warnings", []), []))
            if parsed.path in {"/api/review/blocks", "/api/findings", "/api/cache/findings"}:
                if not path: return _send_json(self, envelope(None, False, [], ["path/root is required"]), 400)
                result = runtime_store.get_scan(path) or self._scan(path)["data"]
                data = {"blocks": result.get("review_blocks", []), "findings": result.get("findings", [])}
                return _send_json(self, envelope(data, True, result.get("warnings", []), []))
            if parsed.path == "/api/review/block":
                block = runtime_store.get_review_block(qs.get("id", [""])[0])
                return _send_json(self, envelope(block, bool(block), [], [] if block else ["block not found"]), 200 if block else 404)
            if parsed.path in {"/api/scan", "/api/cache/scan"}:
                if not path: return _send_json(self, envelope(None, False, [], ["path is required"]), 400)
                return _send_json(self, self._scan(path))
            if parsed.path in {"/api/cache/summary", "/api/cache/folder"}:
                if not path: return _send_json(self, envelope(None, False, [], ["root/path is required"]), 400)
                result = runtime_store.get_scan(path) or self._scan(path)["data"]
                return _send_json(self, envelope({"folderbrain": result.get("folderbrain"), "inventory": (result.get("folderbrain") or {}).get("inventory", {})}, True, result.get("warnings", []), []))
            if parsed.path in {"/api/rename/preview", "/api/rename/baseline-plan", "/api/cache/rename-plan", "/api/cache/rename-sample"}:
                result = runtime_store.get_scan(path) or (self._scan(path)["data"] if path else {"findings": []})
                return _send_json(self, envelope({"rename_findings": [f for f in result.get("findings", []) if f.get("finding_type") == "rename_candidates"], "preview_only": True}))
            if parsed.path in {"/api/manual/scan", "/api/organizer/preview", "/api/cache/classify", "/api/hub/status", "/api/roots", "/api/actions", "/api/cache/files", "/api/cache/clusters", "/api/fingerprint", "/api/folders/compare", "/api/folders/composition"}:
                return _send_json(self, envelope({"status": "compatibility_wrapper", "message": "Endpoint preserved; no destructive action performed.", "preview_only": True}))
            return _send_json(self, envelope(None, False, [], ["not found"]), 404)
        except Exception as exc:
            return _send_json(self, envelope(None, False, [], [str(exc)]), 500)
    def do_POST(self):
        parsed = urlparse(self.path); qs = parse_qs(parsed.query)
        try:
            body = self._body(); path = self._path_from(qs, body)
            if parsed.path == "/api/scan":
                if not path: return _send_json(self, envelope(None, False, [], ["path is required"]), 400)
                return _send_json(self, self._scan(path, body.get("options")))
            if parsed.path == "/api/folderbrain/write":
                if not path: return _send_json(self, envelope(None, False, [], ["path is required"]), 400)
                block = ReviewBlock("folderbrain_summary-001", "folderbrain_summary", "FolderBrain Summary", "Write FolderBrain", 6, "low", 1.0, 0, [], ["write_folderbrain"], {})
                decision = DecisionRecord("api", block.block_id, "write_folderbrain", "approved", body.get("note", ""), body)
                plan = create_plan(block, decision, action="write_folderbrain", folder_path=path, payload={"folderbrain": body.get("folderbrain", {})})
                runtime_store.put_action_plan(plan); return _send_json(self, envelope(to_dict(plan)))
            if parsed.path in {"/api/review/decide", "/api/review/defer", "/api/review/protect", "/api/preferences/record", "/api/decide", "/api/findings/decide"}:
                decision = _decision_from_body(body); runtime_store.put_decision(decision)
                return _send_json(self, envelope(to_dict(decision)))
            if parsed.path == "/api/action/plan":
                block = runtime_store.get_review_block(body.get("block_id", "")) or body.get("block")
                if not block: return _send_json(self, envelope(None, False, [], ["block not found; run /api/scan or pass block"]), 404)
                block_obj = ReviewBlock(**block)
                decision = DecisionRecord("api", block_obj.block_id, body.get("action", "review"), "approved", body.get("note", ""), body)
                plan = create_plan(block_obj, decision, action=body.get("action"), folder_path=path, payload=body)
                runtime_store.put_action_plan(plan); return _send_json(self, envelope(to_dict(plan)))
            if parsed.path == "/api/action/preview":
                plan = _plan_from_dict(body["plan"]) if body.get("plan") else runtime_store.get_action_plan(body.get("plan_id"))
                return _send_json(self, envelope(preview_plan(plan)) if plan else envelope(None, False, [], ["plan not found"]), 200 if plan else 404)
            if parsed.path == "/api/action/approve":
                plan = runtime_store.get_action_plan(body.get("plan_id"))
                if not plan: return _send_json(self, envelope(None, False, [], ["plan not found"]), 404)
                approved = approve_plan(plan, bool(body.get("approved", True))); runtime_store.update_action_plan(approved)
                decision = DecisionRecord(f"decision_{approved.plan_id}", approved.source_block_id, approved.metadata.get("action") or "approve", "approved" if approved.approved else "rejected", body.get("note", ""), body)
                runtime_store.put_decision(decision)
                return _send_json(self, envelope({"plan": to_dict(approved), "safety": to_dict(check_plan(approved, mode="preview"))}))
            if parsed.path == "/api/action/execute":
                plan = runtime_store.get_action_plan(body.get("plan_id"))
                if not plan: return _send_json(self, envelope(None, False, [], ["plan not found"]), 404)
                if not body.get("confirm_execute"):
                    return _send_json(self, envelope({"safety": to_dict(check_plan(plan, mode="execute"))}, False, [], ["confirm_execute=true is required"]), 400)
                executable = executable_copy(plan, True)
                return _send_json(self, envelope(execute_plan(executable)))
            if parsed.path in {"/api/create/folder", "/api/intent", "/api/nlp-classify"}:
                return _send_json(self, envelope({"status": "compatibility_wrapper", "message": "Preview-only compatibility response; no destructive action performed.", "preview_only": True}))
            if parsed.path == "/api/project/export-prompt":
                from scripts.export_project_prompt import export_project_prompt
                return _send_json(self, envelope(export_project_prompt(body.get("root", "."), body.get("output", "FIS_PROJECT_CONTEXT.md"))))
            return _send_json(self, envelope(None, False, [], ["not found"]), 404)
        except Exception as exc:
            return _send_json(self, envelope(None, False, [], [str(exc)]), 500)

def run(host="127.0.0.1", port=8450):
    print(f"River FIS running at http://{host}:{port}/")
    ThreadingHTTPServer((host, port), RiverHandler).serve_forever()
if __name__ == "__main__": run()
