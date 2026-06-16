from app.server import _LAST, _recipes_for, _storyboard
from core.action_plans import create_plan, DISABLED_OPERATIONS, approve_plan
from core.models import DecisionRecord, ReviewBlock
from core.executor import preview_plan, execute_plan


def test_home_story_routes_work(tmp_path):
    (tmp_path / "a.txt").write_text("same")
    (tmp_path / "b.txt").write_text("same")
    recipes = _recipes_for(str(tmp_path))
    assert recipes
    story = _storyboard(recipes[0], str(tmp_path))
    assert story["storyboard_id"] in _LAST["storyboards"]
    assert story["progress"] == ["Found", "Preview", "Safety", "Approve", "Execute", "Record"]


def test_storyboard_approval_does_not_execute(tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("x")
    block = ReviewBlock("rename-001", "rename", "Rename Scheme", "Rename one file", 8, "low", 1.0, 1, [{"path": str(src), "proposed_name": "new.txt"}], ["approve_rename_plan"], {})
    plan = create_plan(block, DecisionRecord("test", block.block_id, "approve_rename_plan", "approved"), action="approve_rename_plan", folder_path=str(tmp_path))
    approved = approve_plan(plan, True)
    assert src.exists()
    assert not (tmp_path / "new.txt").exists()
    assert approved.approved is True


def test_action_lifecycle_from_ui_contract(tmp_path):
    src = tmp_path / "old.txt"
    src.write_text("x")
    block = ReviewBlock("rename-001", "rename", "Rename Scheme", "Rename one file", 8, "low", 1.0, 1, [{"path": str(src), "proposed_name": "new.txt"}], ["approve_rename_plan"], {})
    plan = create_plan(block, DecisionRecord("test", block.block_id, "approve_rename_plan", "approved"), action="approve_rename_plan", folder_path=str(tmp_path))
    preview = preview_plan(plan)
    assert preview["dry_run"] is True
    approved = approve_plan(plan, True)
    result = execute_plan(approved)
    assert result["executed"] is True
    assert (tmp_path / "new.txt").exists()


def test_no_delete_operation_enabled():
    assert "delete" in DISABLED_OPERATIONS
