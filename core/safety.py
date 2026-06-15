from __future__ import annotations
import os
from pathlib import Path
from core.models import ActionPlan, SafetyResult

PROTECTED_NAMES = {".git", ".venv", "venv", "node_modules", "__pycache__", "_gsdata_"}
PROTECTED_FILES = {"preference_engine.db", "sorter_cache.sqlite"}
SYSTEM_MARKERS = ("windows", "program files", "program files (x86)")

def _parts(path: str | None) -> list[str]:
    return [p.lower() for p in Path(path or "").parts]

def _is_protected(path: str | None) -> bool:
    parts = _parts(path)
    if any(p in PROTECTED_NAMES for p in parts):
        return True
    if parts and parts[-1] in PROTECTED_FILES:
        return True
    joined = "\\".join(parts)
    return any(marker in joined for marker in SYSTEM_MARKERS)

def check_plan(plan: ActionPlan, require_dry_run_preview: bool = True, require_decision_record: bool = True) -> SafetyResult:
    blockers: list[str] = []
    warnings: list[str] = []
    approvals: list[str] = []
    if not plan.approved:
        blockers.append("action plan is not approved")
    if plan.dry_run:
        blockers.append("action plan is still dry-run")
    if require_decision_record and not plan.metadata.get("decision"):
        blockers.append("missing decision record")
    for step in plan.steps:
        if step.operation == "delete":
            blockers.append("delete is disabled")
        if _is_protected(step.source) or _is_protected(step.destination):
            blockers.append("target is protected or system path")
        if step.operation in {"rename", "move", "copy", "archive"} and not step.source:
            blockers.append(f"{step.operation} requires source")
        if step.operation in {"rename", "move", "copy", "archive"} and not step.destination:
            blockers.append(f"{step.operation} requires destination")
        if step.destination and os.path.exists(step.destination) and not step.metadata.get("allow_overwrite"):
            blockers.append("destination exists and overwrite was not approved")
        if step.source and step.destination:
            if Path(step.source).drive.lower() != Path(step.destination).drive.lower() and not step.metadata.get("allow_cross_drive"):
                approvals.append("explicit_cross_drive_operation")
                blockers.append("moves across drives require explicit approval")
    return SafetyResult(allowed=not blockers, risk="high" if blockers else ("medium" if warnings or approvals else "low"), blockers=sorted(set(blockers)), warnings=warnings, required_approvals=sorted(set(approvals)))
