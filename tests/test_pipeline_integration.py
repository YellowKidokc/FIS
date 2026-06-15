from __future__ import annotations
import json
from http.client import HTTPConnection
from threading import Thread
from http.server import ThreadingHTTPServer
import pytest
from app.server import RiverHandler
from core.action_plans import create_plan
from core.executor import execute_plan
from core.models import ActionStep, DecisionRecord, ReviewBlock
from core.orchestrator import run_folder_intelligence
from core.safety import check_plan
from engines import duplicates, folderbrain, inventory, naming
from engines.classifier import classify

@pytest.fixture()
def sample_folder(tmp_path):
    root = tmp_path / "sample"; root.mkdir()
    (root / "report.txt").write_text("same report content")
    (root / "report copy.txt").write_text("same report content")
    (root / "badname_A79A36A1.txt").write_text("bad")
    tiny = root / "tiny"; tiny.mkdir(); (tiny / "lone.txt").write_text("one")
    (root / "empty_folder").mkdir()
    data = root / "data"; data.mkdir(); (data / "candles_course.txt").write_text("candles trading course lesson")
    git = root / ".git"; git.mkdir(); (git / "config").write_text("protected")
    return root

def test_orchestrator_returns_folderbrain_findings_blocks(sample_folder):
    result = run_folder_intelligence(str(sample_folder))
    assert not result.get("error")
    assert result["folderbrain"]["folder_name"] == "sample"
    assert result["findings"]
    assert result["review_blocks"]
    assert "timing" in result and "warnings" in result

def test_inventory_detects_extensions_and_tiny_folders(sample_folder):
    scan = inventory.scan(str(sample_folder))
    assert scan["extension_counts"][".txt"] == 5
    assert any("tiny" in f["path"] for f in scan["tiny_folders"])
    assert ".git" in scan["skipped_folders"]

def test_duplicates_create_findings(sample_folder):
    scan = inventory.scan(str(sample_folder)); brain = folderbrain.build(str(sample_folder), {"inventory": scan}, scan)
    findings = duplicates.analyze(brain)
    assert any(f.finding_type == "exact_duplicate" for f in findings)

def test_naming_creates_rename_candidates(sample_folder):
    scan = inventory.scan(str(sample_folder)); brain = folderbrain.build(str(sample_folder), {"inventory": scan}, scan)
    findings = naming.analyze(brain)
    assert findings and findings[0].finding_type == "rename_candidates"
    assert any("hash_or_uuid_like" in item["reasons"] for item in findings[0].items)

def test_low_confidence_classification_needs_review(sample_folder):
    scan = inventory.scan(str(sample_folder)); brain = folderbrain.build(str(sample_folder), {"inventory": scan}, scan)
    result = classify(brain)
    assert result["needs_review"] is True

def test_review_blocks_group_findings(sample_folder):
    result = run_folder_intelligence(str(sample_folder))
    block_types = {b["block_type"] for b in result["review_blocks"]}
    assert "duplicates" in block_types
    assert "tiny_folder" in block_types
    assert "rename" in block_types

def test_action_plan_defaults_dry_run_unapproved(sample_folder):
    block = ReviewBlock("b1", "rename", "Rename", "", 8, "medium", .8, 0, [], [], {})
    plan = create_plan(block, DecisionRecord("d1", "b1", "preview_names", "approved"), [ActionStep("rename", str(sample_folder / "report.txt"), str(sample_folder / "report-renamed.txt"))])
    assert plan.dry_run is True and plan.approved is False

def test_executor_refuses_unapproved_plan(sample_folder):
    block = ReviewBlock("b1", "rename", "Rename", "", 8, "medium", .8, 0, [], [], {})
    plan = create_plan(block, DecisionRecord("d1", "b1", "preview_names", "approved"), [ActionStep("rename", str(sample_folder / "report.txt"), str(sample_folder / "report-renamed.txt"))])
    result = execute_plan(plan)
    assert result["executed"] is False
    assert "Plan is not approved" in result["safety"]["blockers"]

def test_safety_blocks_delete(sample_folder):
    block = ReviewBlock("b1", "x", "x", "", 1, "high", .1, 0, [], [], {})
    plan = create_plan(block, DecisionRecord("d1", "b1", "delete", "approved"), [ActionStep("delete", str(sample_folder / "report.txt"))])
    result = check_plan(plan)
    assert "Delete is disabled" in result.blockers

def test_safety_blocks_protected_paths(sample_folder):
    block = ReviewBlock("b1", "x", "x", "", 1, "high", .1, 0, [], [], {})
    plan = create_plan(block, DecisionRecord("d1", "b1", "move", "approved"), [ActionStep("move", str(sample_folder / ".git" / "config"), str(sample_folder / "config"))])
    result = check_plan(plan)
    assert "Target is protected or system path" in result.blockers

def test_api_scan_and_review_blocks(sample_folder):
    server = ThreadingHTTPServer(("127.0.0.1", 0), RiverHandler)
    thread = Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        conn = HTTPConnection("127.0.0.1", server.server_port)
        conn.request("POST", "/api/scan", body=json.dumps({"path": str(sample_folder)}), headers={"Content-Type": "application/json"})
        res = conn.getresponse(); payload = json.loads(res.read())
        assert res.status == 200 and payload["review_blocks"]
        conn.request("GET", f"/api/review/blocks?path={sample_folder}")
        res = conn.getresponse(); payload = json.loads(res.read())
        assert res.status == 200 and payload["blocks"]
    finally:
        server.shutdown(); server.server_close()
