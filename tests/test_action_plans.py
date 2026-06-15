from core.action_plans import create_plan
from core.models import ActionStep, DecisionRecord, ReviewBlock


def block():
    return ReviewBlock("rename-001", "rename", "Rename", "", 8, "medium", 0.8, 0, [], [], {})


def test_action_plans_are_dry_run_by_default():
    decision = DecisionRecord("d1", "rename-001", "preview_names", "approved")
    plan = create_plan(block(), decision, [ActionStep("rename", "a.txt", "b.txt")])
    assert plan.dry_run is True
    assert plan.approved is False
