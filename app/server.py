from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from core.models import ActionPlan, ActionStep, DecisionRecord, ReviewBlock, to_dict
from core.orchestrator import run_folder_intelligence
from core.action_plans import create_plan, approve_plan
from core.executor import preview_plan, execute_plan
from core.safety import check_plan

_LAST = {"plans": {}, "blocks": {}, "results": {}, "decisions": []}

def _send(handler, payload, status=200):
    data = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status); handler.send_header("Content-Type", "application/json"); handler.send_header("Access-Control-Allow-Origin", "*"); handler.send_header("Access-Control-Allow-Headers", "Content-Type"); handler.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS"); handler.send_header("Content-Length", str(len(data))); handler.end_headers(); handler.wfile.write(data)

def _block_from_store(block_id: str) -> ReviewBlock | None:
    data = _LAST["blocks"].get(block_id)
    return ReviewBlock(**data) if data else None

def _plan_from_dict(data: dict) -> ActionPlan:
    return ActionPlan(data["plan_id"], data["source_block_id"], data["dry_run"], data["approved"], [ActionStep(**s) for s in data.get("steps", [])], data.get("created_by", "river"), data.get("metadata", {}))

class RiverHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): return
    def do_OPTIONS(self): _send(self, {"ok": True})
    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(length) or b"{}") if length else {}
    def _path_from(self, qs, body=None): return (body or {}).get("path") or qs.get("path", qs.get("root", [""]))[0]
    def _run(self, path, options=None):
        result = run_folder_intelligence(path, options)
        if not result.get("error"):
            _LAST["results"][path] = result
            for block in result["review_blocks"]: _LAST["blocks"][block["block_id"]] = block
        return result
    def do_GET(self):
        parsed = urlparse(self.path); qs = parse_qs(parsed.query); path = self._path_from(qs)
        if parsed.path == "/api/health": return _send(self, {"ok": True, "service": "River FIS", "guided": True})
        if parsed.path in {"/api/cache/status", "/api/stats"}: return _send(self, {"ok": True, "memory_plans": len(_LAST["plans"]), "memory_blocks": len(_LAST["blocks"]), "decisions": len(_LAST["decisions"])})
        if parsed.path in {"/api/folderbrain", "/api/cache/folderbrain"}:
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, self._run(path).get("folderbrain"))
        if parsed.path in {"/api/review/blocks", "/api/findings", "/api/cache/findings"}:
            if not path: return _send(self, {"error": "path/root is required"}, 400)
            result = self._run(path)
            return _send(self, {"blocks": result.get("review_blocks", []), "findings": result.get("findings", []), "warnings": result.get("warnings", [])})
        if parsed.path == "/api/review/block":
            block_id = qs.get("id", [""])[0]; exists = block_id in _LAST["blocks"]
            return _send(self, _LAST["blocks"].get(block_id, {"error": "block not found"}), 200 if exists else 404)
        if parsed.path in {"/api/cache/summary", "/api/cache/folder"}:
            if not path: return _send(self, {"error": "root/path is required"}, 400)
            result = self._run(path); return _send(self, {"folderbrain": result.get("folderbrain"), "inventory": (result.get("folderbrain") or {}).get("inventory", {})})
        if parsed.path in {"/api/scan", "/api/cache/scan"}:
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, self._run(path))
        if parsed.path in {"/api/rename/preview", "/api/rename/baseline-plan", "/api/cache/rename-plan", "/api/cache/rename-sample"}:
            result = self._run(path) if path else {"findings": []}
            rename = [f for f in result.get("findings", []) if f.get("finding_type") == "rename_candidates"]
            return _send(self, {"ok": True, "rename_findings": rename, "preview_only": True})
        if parsed.path in {"/api/manual/scan", "/api/organizer/preview", "/api/cache/classify", "/api/hub/status", "/api/roots", "/api/actions", "/api/cache/files", "/api/cache/clusters", "/api/fingerprint", "/api/folders/compare", "/api/folders/composition"}:
            return _send(self, {"ok": True, "status": "compatibility_wrapper", "message": "Endpoint preserved; full legacy behavior is being harvested. No destructive action performed.", "preview_only": True})
        return _send(self, {"error": "not found"}, 404)
    def do_POST(self):
        parsed = urlparse(self.path); body = self._body(); qs = parse_qs(parsed.query); path = self._path_from(qs, body)
        if parsed.path == "/api/scan":
            if not path: return _send(self, {"error": "path is required"}, 400)
            return _send(self, self._run(path, body.get("options")))
        if parsed.path == "/api/folderbrain/write":
            block = ReviewBlock("folderbrain_summary-001", "folderbrain_summary", "FolderBrain Summary", "Write FolderBrain", 6, "low", 1.0, 0, [], ["write_folderbrain"], {})
            decision = DecisionRecord("api", block.block_id, "write_folderbrain", "approved", body.get("note", ""))
            plan = create_plan(block, decision, action="write_folderbrain", folder_path=path, payload={"folderbrain": body.get("folderbrain", {})})
            _LAST["plans"][plan.plan_id] = plan; return _send(self, to_dict(plan))
        if parsed.path in {"/api/review/decide", "/api/review/defer", "/api/review/protect", "/api/preferences/record", "/api/decide", "/api/findings/decide"}:
            _LAST["decisions"].append(body); return _send(self, {"recorded": True, "decision": body, "preview_only": True})
        if parsed.path == "/api/action/plan":
            block = _block_from_store(body.get("block_id", "")) or (ReviewBlock(**body["block"]) if body.get("block") else None)
            if not block: return _send(self, {"error": "block not found; run /api/scan or pass block"}, 404)
            decision = DecisionRecord("api", block.block_id, body.get("action", "review"), "approved", body.get("note", ""))
            plan = create_plan(block, decision, action=body.get("action"), folder_path=path, payload=body)
            _LAST["plans"][plan.plan_id] = plan; return _send(self, to_dict(plan))
        if parsed.path == "/api/action/preview":
            plan = _plan_from_dict(body["plan"]) if body.get("plan") else _LAST["plans"].get(body.get("plan_id"))
            return _send(self, preview_plan(plan) if plan else {"error": "plan not found"}, 200 if plan else 404)
        if parsed.path == "/api/action/approve":
            plan = _LAST["plans"].get(body.get("plan_id"))
            if not plan: return _send(self, {"error": "plan not found"}, 404)
            plan = approve_plan(plan, bool(body.get("approved", True))); _LAST["plans"][plan.plan_id] = plan
            return _send(self, {"plan": to_dict(plan), "safety": to_dict(check_plan(plan))})
        if parsed.path == "/api/action/execute":
            plan = _LAST["plans"].get(body.get("plan_id")); return _send(self, execute_plan(plan) if plan else {"error":"plan not found"}, 200 if plan else 404)
        if parsed.path in {"/api/create/folder", "/api/intent", "/api/nlp-classify"}:
            return _send(self, {"ok": True, "status": "compatibility_wrapper", "message": "Preview-only compatibility response; no destructive action performed.", "preview_only": True})
        if parsed.path == "/api/project/export-prompt":
            from scripts.export_project_prompt import export_project_prompt
            return _send(self, export_project_prompt(body.get("root", "."), body.get("output", "FIS_PROJECT_CONTEXT.md")))
        return _send(self, {"error": "not found"}, 404)

def run(host="127.0.0.1", port=8450): ThreadingHTTPServer((host, port), RiverHandler).serve_forever()
if __name__ == "__main__": run()
