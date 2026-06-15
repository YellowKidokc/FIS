from __future__ import annotations
from pathlib import Path
from uuid import uuid4
from core.models import ActionPlan, ActionStep, DecisionRecord, ReviewBlock

ALLOWED_OPERATIONS = {"create_folder", "write_folderbrain", "rename", "move", "copy", "archive", "zip_backup", "tag", "protect", "link_hub"}
DISABLED_OPERATIONS = {"delete"}

def _archive_destination(path: str) -> str:
    p = Path(path)
    return str(p.parent / "_river_review_archive" / p.name)

def steps_for_decision(block: ReviewBlock, action: str, folder_path: str, payload: dict | None = None) -> list[ActionStep]:
    payload = payload or {}
    steps: list[ActionStep] = []
    if action == "write_folderbrain":
        steps.append(ActionStep("write_folderbrain", destination=str(Path(folder_path) / ".folderbrain.json"), reason="Write approved FolderBrain metadata", risk="low", metadata={"folderbrain": payload.get("folderbrain", {})}))
    elif action in {"archive_extra_copy", "archive_empty", "archive_residue", "archive_review"}:
        for item in payload.get("items", block.items or []):
            source = item.get("path") or item.get("source")
            if source: steps.append(ActionStep("archive", source=source, destination=_archive_destination(source), reason=f"Approved {action} from {block.block_id}", risk="medium"))
    elif action in {"preview_names", "approve_rename_plan"}:
        for item in payload.get("items", block.items or []):
            source = item.get("path")
            proposed = item.get("proposed_name")
            if source and proposed:
                steps.append(ActionStep("rename", source=source, destination=str(Path(source).with_name(proposed)), reason="Approved rename candidate", risk="medium"))
    elif action == "protect_folder":
        steps.append(ActionStep("protect", source=folder_path, reason="Mark folder protected in River metadata", risk="low"))
    elif action == "create_hub":
        steps.append(ActionStep("link_hub", source=folder_path, destination=str(Path(folder_path) / "_river_hub.md"), reason="Create hub link page after approval", risk="low"))
    elif action == "create_missing_folders":
        for name in payload.get("folders", []): steps.append(ActionStep("create_folder", destination=str(Path(folder_path) / name), reason="Create approved template folder", risk="low"))
    return steps

def create_plan(block: ReviewBlock, decision: DecisionRecord | None = None, steps: list[ActionStep] | None = None, action: str | None = None, folder_path: str | None = None, payload: dict | None = None) -> ActionPlan:
    real_steps = steps if steps is not None else steps_for_decision(block, action or getattr(decision, "action", ""), folder_path or "", payload)
    normalized = []
    for step in real_steps or []:
        if step.operation == "delete": step.risk = "high"
        normalized.append(step)
    return ActionPlan(f"plan_{uuid4().hex[:12]}", block.block_id, True, False, normalized, metadata={"decision": getattr(decision, "decision", None), "action": action or getattr(decision, "action", None), "folder_path": folder_path})

def approve_plan(plan: ActionPlan, approved: bool = True) -> ActionPlan:
    return ActionPlan(plan.plan_id, plan.source_block_id, dry_run=not approved, approved=approved, steps=plan.steps, created_by=plan.created_by, metadata={**plan.metadata, "approved": approved, "explicit_execute": approved})
