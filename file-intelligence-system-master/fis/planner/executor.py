from __future__ import annotations
from uuid import uuid4
from .simulator import simulate_plan


def execute_plan(plan_id: str, confirmation: str) -> dict:
    if confirmation != "APPROVE":
        return {"plan_id": plan_id, "status": "blocked", "error": "confirmation must be APPROVE"}
    sim = simulate_plan(plan_id)
    if not sim.get("safe_to_run"):
        return {"plan_id": plan_id, "status": "blocked", "simulation": sim}
    txn_id = "txn_" + uuid4().hex
    # First pass is intentionally stubbed: no filesystem mutation without a full ledger implementation.
    return {"plan_id": plan_id, "txn_id": txn_id, "status": "stubbed_preview_only", "message": "Execution is gated; full two-phase commit is not enabled in this pass.", "simulation": sim}
