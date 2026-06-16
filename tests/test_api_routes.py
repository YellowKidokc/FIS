from __future__ import annotations
import json
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from threading import Thread
import pytest
from app.server import RiverHandler

@pytest.fixture()
def sample_folder(tmp_path):
    root = tmp_path / "sample"; root.mkdir()
    (root / "report.txt").write_text("same")
    (root / "report copy.txt").write_text("same")
    (root / "badname_A79A36A1.txt").write_text("bad")
    (root / "tiny").mkdir(); (root / "tiny" / "lone.txt").write_text("one")
    (root / "empty_folder").mkdir()
    (root / ".git").mkdir(); (root / ".git" / "config").write_text("protected")
    return root

@pytest.fixture()
def api():
    server = ThreadingHTTPServer(("127.0.0.1", 0), RiverHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    def request(method, path, payload=None):
        conn = HTTPConnection("127.0.0.1", server.server_port)
        body = json.dumps(payload).encode() if payload is not None else None
        conn.request(method, path, body=body, headers={"Content-Type": "application/json"} if body else {})
        res = conn.getresponse(); data = json.loads(res.read())
        conn.close(); return res.status, data
    yield request
    server.shutdown(); server.server_close()

def test_health_endpoint(api):
    status, body = api("GET", "/api/health")
    assert status == 200 and body["ok"] is True and body["data"]["api_base"] == "/api"

def test_scan_endpoint_returns_folderbrain_findings_blocks(api, sample_folder):
    status, body = api("POST", "/api/scan", {"path": str(sample_folder)})
    data = body["data"]
    assert status == 200 and body["ok"] is True
    assert data["folderbrain"] and data["findings"] and data["review_blocks"]

def test_review_blocks_endpoint_after_scan(api, sample_folder):
    api("POST", "/api/scan", {"path": str(sample_folder)})
    status, body = api("GET", f"/api/review/blocks?path={sample_folder}")
    assert status == 200 and body["data"]["blocks"]

def test_action_plan_endpoint_creates_dry_run_unapproved_plan(api, sample_folder):
    _, scan = api("POST", "/api/scan", {"path": str(sample_folder)})
    block_id = scan["data"]["review_blocks"][0]["block_id"]
    status, body = api("POST", "/api/action/plan", {"path": str(sample_folder), "block_id": block_id, "action": "create_missing_folders", "folders": ["approved_folder"]})
    plan = body["data"]
    assert status == 200 and plan["dry_run"] is True and plan["approved"] is False

def test_action_preview_does_not_execute(api, sample_folder):
    _, scan = api("POST", "/api/scan", {"path": str(sample_folder)})
    block_id = scan["data"]["review_blocks"][0]["block_id"]
    _, planned = api("POST", "/api/action/plan", {"path": str(sample_folder), "block_id": block_id, "action": "create_missing_folders", "folders": ["preview_only"]})
    status, preview = api("POST", "/api/action/preview", {"plan_id": planned["data"]["plan_id"]})
    assert status == 200 and preview["data"]["safety"]["allowed"] is True
    assert not (sample_folder / "preview_only").exists()

def test_action_approve_marks_plan_approved_but_dry_run(api, sample_folder):
    _, scan = api("POST", "/api/scan", {"path": str(sample_folder)})
    block_id = scan["data"]["review_blocks"][0]["block_id"]
    _, planned = api("POST", "/api/action/plan", {"path": str(sample_folder), "block_id": block_id, "action": "create_missing_folders", "folders": ["approved_folder"]})
    status, approved = api("POST", "/api/action/approve", {"plan_id": planned["data"]["plan_id"], "approved": True})
    plan = approved["data"]["plan"]
    assert status == 200 and plan["approved"] is True and plan["dry_run"] is True

def test_action_execute_requires_confirm_execute(api, sample_folder):
    _, scan = api("POST", "/api/scan", {"path": str(sample_folder)})
    block_id = scan["data"]["review_blocks"][0]["block_id"]
    _, planned = api("POST", "/api/action/plan", {"path": str(sample_folder), "block_id": block_id, "action": "create_missing_folders", "folders": ["needs_confirm"]})
    api("POST", "/api/action/approve", {"plan_id": planned["data"]["plan_id"], "approved": True})
    status, executed = api("POST", "/api/action/execute", {"plan_id": planned["data"]["plan_id"]})
    assert status == 400 and executed["ok"] is False
    assert not (sample_folder / "needs_confirm").exists()

def test_action_execute_blocks_unapproved_plan(api, sample_folder):
    _, scan = api("POST", "/api/scan", {"path": str(sample_folder)})
    block_id = scan["data"]["review_blocks"][0]["block_id"]
    _, planned = api("POST", "/api/action/plan", {"path": str(sample_folder), "block_id": block_id, "action": "create_missing_folders", "folders": ["blocked"]})
    status, executed = api("POST", "/api/action/execute", {"plan_id": planned["data"]["plan_id"], "confirm_execute": True})
    assert status == 200 and executed["data"]["executed"] is False
    assert "Plan is not approved" in executed["data"]["safety"]["blockers"]

def test_action_execute_blocks_delete(api, sample_folder):
    block = {"block_id": "danger-001", "block_type": "danger", "title": "Danger", "summary": "", "weight": 10, "risk": "high", "confidence": 1.0, "item_count": 0, "items": [], "suggested_actions": [], "evidence": {}}
    plan = {"plan_id": "client_delete", "source_block_id": "danger-001", "dry_run": True, "approved": False, "steps": [{"operation": "delete", "source": str(sample_folder / "report.txt"), "destination": None, "reason": "", "risk": "high", "metadata": {}}], "created_by": "test", "metadata": {"decision": "approved"}}
    status, preview = api("POST", "/api/action/preview", {"plan": plan})
    assert status == 200 and "Delete is disabled" in preview["data"]["safety"]["blockers"]

def test_folderbrain_write_requires_action_plan_or_explicit_endpoint(api, sample_folder):
    status, body = api("POST", "/api/folderbrain/write", {"path": str(sample_folder), "folderbrain": {"ok": True}})
    plan = body["data"]
    assert status == 200 and plan["steps"][0]["operation"] == "write_folderbrain"
    assert plan["dry_run"] is True and not (sample_folder / ".folderbrain.json").exists()
