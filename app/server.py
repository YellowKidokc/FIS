from __future__ import annotations
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from core.models import ActionStep, DecisionRecord, ReviewBlock, to_dict
from core.orchestrator import run_folder_intelligence
from core.action_plans import create_plan, approve_plan
from core.executor import preview_plan, execute_plan
from core.safety import check_plan

_LAST = {"plans": {}, "blocks": {}}

def _send(handler, payload, status=200):
    data = json.dumps(payload, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers(); handler.wfile.write(data)

class RiverHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        _send(self, {"ok": True})
    def _body(self):
        length = int(self.headers.get("Content-Length", 0) or 0)
        return json.loads(self.rfile.read(length) or b"{}") if length else {}
    def do_GET(self):
        parsed = urlparse(self.path); qs = parse_qs(parsed.query)
        if parsed.path == "/api/health": return _send(self, {"ok": True, "service": "River FIS", "guided": True})
        if parsed.path == "/api/cache/status": return _send(self, {"ok": True, "memory_plans": len(_LAST["plans"]), "memory_blocks": len(_LAST["blocks"])})
        if parsed.path in {"/api/folderbrain", "/api/review/blocks"}:
            path = qs.get("path", [""])[0]
            if not path: return _send(self, {"error": "path is required"}, 400)
            result = run_folder_intelligence(path)
            for block in result["review_blocks"]: _LAST["blocks"][block["block_id"]] = block
            if parsed.path == "/api/folderbrain": return _send(self, result["folderbrain"])
            return _send(self, {"blocks": result["review_blocks"]})
        if parsed.path == "/api/review/block":
            block_id = qs.get("id", [""])[0]
            return _send(self, _LAST["blocks"].get(block_id, {"error": "block not found"}), 404 if block_id not in _LAST["blocks"] else 200)
        return _send(self, {"error": "not found"}, 404)
    def do_POST(self):
        parsed = urlparse(self.path); body = self._body()
        if parsed.path == "/api/scan":
            path = body.get("path")
            if not path: return _send(self, {"error": "path is required"}, 400)
            result = run_folder_intelligence(path, body.get("options"))
            for block in result["review_blocks"]: _LAST["blocks"][block["block_id"]] = block
            return _send(self, result)
        if parsed.path in {"/api/review/decide", "/api/review/defer", "/api/review/protect", "/api/preferences/record"}:
            return _send(self, {"recorded": True, "decision": body})
        if parsed.path == "/api/action/plan":
            block = ReviewBlock(**body.get("block", _LAST["blocks"].get(body.get("block_id"), {})))
            steps = [ActionStep(**s) for s in body.get("steps", [])]
            decision = DecisionRecord(**body["decision"]) if body.get("decision") else None
            plan = create_plan(block, decision, steps); _LAST["plans"][plan.plan_id] = plan
            return _send(self, to_dict(plan))
        if parsed.path == "/api/action/preview":
            plan = _LAST["plans"].get(body.get("plan_id")); return _send(self, preview_plan(plan) if plan else {"error":"plan not found"}, 404 if not plan else 200)
        if parsed.path == "/api/action/approve":
            plan = _LAST["plans"].get(body.get("plan_id"))
            if not plan: return _send(self, {"error":"plan not found"}, 404)
            plan = approve_plan(plan); _LAST["plans"][plan.plan_id] = plan
            return _send(self, {"plan": to_dict(plan), "safety": to_dict(check_plan(plan))})
        if parsed.path == "/api/action/execute":
            plan = _LAST["plans"].get(body.get("plan_id")); return _send(self, execute_plan(plan) if plan else {"error":"plan not found"}, 404 if not plan else 200)
        if parsed.path == "/api/preferences/stats": return _send(self, {"decisions": 0})
        if parsed.path == "/api/project/export-prompt":
            from scripts.export_project_prompt import export_project_prompt
            return _send(self, export_project_prompt(body.get("root", "."), body.get("output", "FIS_PROJECT_CONTEXT.md")))
        return _send(self, {"error": "not found"}, 404)

def run(host="127.0.0.1", port=8450):
    ThreadingHTTPServer((host, port), RiverHandler).serve_forever()

if __name__ == "__main__":
    run()
