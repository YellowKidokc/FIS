from __future__ import annotations
from uuid import uuid4
from core.models import ActionPlan, ActionStep, DecisionRecord, ReviewBlock

ALLOWED_OPERATIONS = {"create_folder", "write_folderbrain", "rename", "move", "copy", "archive", "zip_backup", "tag", "protect", "link_hub"}
DISABLED_OPERATIONS = {"delete"}

def create_plan(block: ReviewBlock, decision: DecisionRecord | None = None, steps: list[ActionStep] | None = None) -> ActionPlan:
    normalized = []
    for step in steps or []:
        if step.operation == "delete":
            step.risk = "high"
        normalized.append(step)
    return ActionPlan(plan_id=f"plan_{uuid4().hex[:12]}", source_block_id=block.block_id, dry_run=True, approved=False, steps=normalized, metadata={"decision": getattr(decision, "decision", None)})

def approve_plan(plan: ActionPlan) -> ActionPlan:
    return ActionPlan(plan_id=plan.plan_id, source_block_id=plan.source_block_id, dry_run=False, approved=True, steps=plan.steps, created_by=plan.created_by, metadata={**plan.metadata, "approved": True})
