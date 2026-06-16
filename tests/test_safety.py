from core.action_plans import approve_plan, create_plan
from core.models import ActionStep, DecisionRecord, ReviewBlock
from core.safety import check_plan


def block():
    return ReviewBlock("b1", "duplicates", "Dupes", "", 9, "medium", 0.9, 0, [], [], {})


def test_safety_blocks_delete():
    p = create_plan(block(), DecisionRecord("d1", "b1", "archive", "approved"), [ActionStep("delete", "a.txt")])
    result = check_plan(approve_plan(p))
    assert not result.allowed
    assert "Delete is disabled" in result.blockers


def test_safety_blocks_unapproved_move():
    p = create_plan(block(), DecisionRecord("d1", "b1", "move", "approved"), [ActionStep("move", "a.txt", "b.txt")])
    result = check_plan(p, mode="execute")
    assert not result.allowed
    assert "Plan is not approved" in result.blockers


def test_safety_blocks_protected_paths():
    p = create_plan(block(), DecisionRecord("d1", "b1", "move", "approved"), [ActionStep("move", "/repo/.git/config", "/tmp/config")])
    result = check_plan(approve_plan(p))
    assert not result.allowed
    assert "Target is protected or system path" in result.blockers
