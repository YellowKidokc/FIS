from __future__ import annotations
from dataclasses import dataclass, asdict
from uuid import uuid4
from typing import Any
from core.action_plans import create_plan
from core.executor import preview_plan
from core.models import DecisionRecord, ReviewBlock
from core.recipes import RecipeCandidate

@dataclass
class Storyboard:
    storyboard_id: str
    recipe_id: str
    title: str
    subtitle: str
    folder_path: str
    status: str
    risk: str
    confidence: float
    summary_cards: list[dict]
    story_steps: list[dict]
    preview_items: list[dict]
    safety: dict
    available_decisions: list[str]
    linked_action_plan_id: str | None = None

VISUAL_BY_RECIPE = {
    "clean_duplicates": "duplicate_stack",
    "clean_names": "rename_before_after",
    "sort_by_composition": "move_arrow",
    "separate_mixed_folder": "move_arrow",
    "build_similar_hub": "hub_links",
    "archive_old_or_junk": "archive_box",
    "create_folder_template": "folder_scan",
    "review_low_confidence": "report_card",
    "build_memory": "folder_scan",
    "create_automation_rule": "approval_gate",
}
ACTION_BY_RECIPE = {
    "clean_duplicates": "archive_extra_copy",
    "clean_names": "preview_names",
    "sort_by_composition": "create_missing_folders",
    "separate_mixed_folder": "create_missing_folders",
    "build_similar_hub": "create_hub",
    "archive_old_or_junk": "archive_residue",
    "create_folder_template": "create_missing_folders",
    "review_low_confidence": "protect_folder",
    "build_memory": "write_folderbrain",
    "create_automation_rule": "save_preference",
}

def to_dict(storyboard: Storyboard) -> dict[str, Any]: return asdict(storyboard)

def _source_blocks(scan_result: dict, recipe: RecipeCandidate) -> list[dict]:
    blocks = scan_result.get("review_blocks", []) if scan_result else []
    ids = set(recipe.source_blocks)
    return [b for b in blocks if b.get("block_id") in ids]

def _preview_items(blocks: list[dict]) -> list[dict]:
    items = []
    for block in blocks:
        for item in block.get("items", [])[:10]:
            items.append({"block_id": block.get("block_id"), "block_type": block.get("block_type"), "item": item})
    return items[:25]

def _summary_cards(recipe: RecipeCandidate, blocks: list[dict]) -> list[dict]:
    affected = sum(int(b.get("item_count", 0) or 0) for b in blocks)
    return [
        {"label": "What River found", "value": recipe.reason, "tone": "gold"},
        {"label": "Affected items", "value": affected, "tone": "blue"},
        {"label": "What will NOT be touched", "value": "Protected folders, databases, system folders, and unknown high-risk paths stay untouched.", "tone": "safe"},
    ]

def _steps(recipe: RecipeCandidate, blocks: list[dict], plan_preview: dict | None) -> list[dict]:
    affected = sum(int(b.get("item_count", 0) or 0) for b in blocks)
    visual = VISUAL_BY_RECIPE.get(recipe.recipe_type, "report_card")
    safety = (plan_preview or {}).get("safety", {})
    return [
        {"step_id": "found", "title": "Found", "sentence": recipe.one_sentence, "visual_type": "folder_scan", "status": "complete", "operation": "scan", "source_count": affected, "destination_count": 0, "risk": recipe.risk, "details_collapsed": True},
        {"step_id": "preview", "title": "Preview", "sentence": "River will build a dry-run plan first. No files change during preview.", "visual_type": visual, "status": "ready", "operation": ACTION_BY_RECIPE.get(recipe.recipe_type, "review"), "source_count": affected, "destination_count": len((plan_preview or {}).get("steps", [])), "risk": recipe.risk, "details_collapsed": True},
        {"step_id": "safety", "title": "Safety", "sentence": "Safety checks protected paths, overwrites, databases, and execution confirmation before anything runs.", "visual_type": "safety_gate", "status": "blocked" if safety.get("blockers") else "ready", "operation": "safety_check", "source_count": affected, "destination_count": 0, "risk": safety.get("risk", recipe.risk), "details_collapsed": True},
        {"step_id": "approval", "title": "Approve", "sentence": "You can approve, edit, skip, or defer. Approval records the plan but does not execute it directly.", "visual_type": "approval_gate", "status": "waiting", "operation": "decision", "source_count": affected, "destination_count": 0, "risk": recipe.risk, "details_collapsed": True},
    ]

def build_storyboard(recipe: RecipeCandidate, scan_result: dict, action_plan=None) -> tuple[Storyboard, object | None]:
    blocks = _source_blocks(scan_result, recipe)
    plan = action_plan
    plan_preview = None
    if plan is None and recipe.recipe_type not in {"create_automation_rule"}:
        block_data = blocks[0] if blocks else {"block_id": f"{recipe.recipe_type}-story", "block_type": recipe.recipe_type, "title": recipe.title, "summary": recipe.one_sentence, "weight": 5, "risk": recipe.risk, "confidence": recipe.confidence, "item_count": 0, "items": [], "suggested_actions": recipe.suggested_actions, "evidence": {}}
        block = ReviewBlock(**block_data)
        decision = DecisionRecord(f"decision_{uuid4().hex[:8]}", block.block_id, ACTION_BY_RECIPE.get(recipe.recipe_type, "review"), "pending", payload={"path": recipe.folder_path, "recipe_id": recipe.recipe_id})
        plan = create_plan(block, decision, action=ACTION_BY_RECIPE.get(recipe.recipe_type), folder_path=recipe.folder_path, payload={"folders": ["_river_review"], "items": block.items, "folderbrain": (scan_result or {}).get("folderbrain", {})})
        plan_preview = preview_plan(plan)
    elif plan is not None:
        plan_preview = preview_plan(plan)
    storyboard = Storyboard(
        storyboard_id=f"story_{uuid4().hex[:12]}", recipe_id=recipe.recipe_id, title=recipe.title, subtitle=recipe.subtitle, folder_path=recipe.folder_path, status="draft", risk=recipe.risk, confidence=recipe.confidence, summary_cards=_summary_cards(recipe, blocks), story_steps=_steps(recipe, blocks, plan_preview), preview_items=_preview_items(blocks), safety=(plan_preview or {"safety": {}}).get("safety", {}), available_decisions=["approve", "edit", "skip", "defer"], linked_action_plan_id=getattr(plan, "plan_id", None))
    return storyboard, plan
