from __future__ import annotations
from .simple_strategies import PLANS


def simulate_plan(plan_id: str) -> dict:
    plan = PLANS.get(plan_id)
    if not plan:
        raise KeyError(plan_id)
    blocked = [w for w in plan.get("warnings", []) if "Block" in w or "cannot" in w or "requires" in w]
    counts = {"would_change": 0, "would_move": 0, "would_rename": 0, "would_recycle": 0, "would_create_folders": 0}
    for action in plan.get("actions", []):
        if action.get("safety") == "blocked" or action.get("type") == "skip":
            continue
        counts["would_change"] += 1
        if action.get("type") in {"move", "copy"}: counts["would_move"] += 1
        if action.get("type") == "rename": counts["would_rename"] += 1
        if action.get("type") in {"recycle", "deduplicate", "archive"}: counts["would_recycle"] += 1
        if action.get("type") == "create_folder": counts["would_create_folders"] += 1
    return {"plan_id": plan_id, "safe_to_run": not blocked, **counts, "blocked": blocked, "warnings": plan.get("warnings", []), "preview_rows": plan.get("preview", [])}
