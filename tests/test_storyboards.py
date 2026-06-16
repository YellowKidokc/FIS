from core.orchestrator import run_folder_intelligence
from core.recipes import build_recipe_candidates
from core.runtime_store import RuntimeStore
from core.storyboards import build_storyboard
from core.models import DecisionRecord


def make_sample(tmp_path):
    root = tmp_path / "sample"; root.mkdir()
    (root / "report.txt").write_text("same")
    (root / "report copy.txt").write_text("same")
    (root / "badname_A79A36A1.txt").write_text("bad")
    return root


def test_storyboard_builds_from_recipe(tmp_path):
    root = make_sample(tmp_path)
    result = run_folder_intelligence(str(root))
    recipe = build_recipe_candidates(result, str(root))[0]
    storyboard, plan = build_storyboard(recipe, result)
    assert storyboard.title
    assert storyboard.story_steps
    assert storyboard.available_decisions == ["approve", "edit", "skip", "defer"]


def test_storyboard_links_to_dry_run_action_plan(tmp_path):
    root = make_sample(tmp_path)
    result = run_folder_intelligence(str(root))
    recipe = next(r for r in build_recipe_candidates(result, str(root)) if r.recipe_type == "clean_duplicates")
    storyboard, plan = build_storyboard(recipe, result)
    assert plan is not None
    assert storyboard.linked_action_plan_id == plan.plan_id
    assert plan.dry_run is True and plan.approved is False


def test_storyboard_approval_does_not_execute(tmp_path):
    root = make_sample(tmp_path)
    result = run_folder_intelligence(str(root))
    recipe = build_recipe_candidates(result, str(root))[0]
    storyboard, plan = build_storyboard(recipe, result)
    store = RuntimeStore(); store.put_storyboard(storyboard); store.put_action_plan(plan)
    decision = DecisionRecord("d1", storyboard.storyboard_id, "storyboard", "approved", payload={"storyboard_id": storyboard.storyboard_id})
    store.put_decision(decision)
    assert store.get_action_plan(plan.plan_id).dry_run is True
    assert not (root / "_river_review").exists()
