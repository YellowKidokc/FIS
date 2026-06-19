from __future__ import annotations
from pathlib import Path
from core.models import ActionPlan, SafetyResult

PROTECTED_NAMES = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", "_gsdata_"}
PROTECTED_FILES = {"preference_engine.db", "sorter_cache.sqlite"}
LEDGER_SUFFIXES = {".meqlog", ".orgledger"}
DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
SYSTEM_MARKERS = ("windows", "program files", "program files (x86)")
SUPPORTED_OPERATIONS = {"create_folder", "write_folderbrain", "rename", "move", "copy", "archive", "zip_backup", "tag", "protect", "link_hub", "delete"}
LOW_RISK_EXECUTE = {"create_folder", "write_folderbrain", "copy", "zip_backup", "protect", "link_hub"}
GUARDED_NOT_IMPLEMENTED = {"rename", "move", "archive", "tag"}

def _parts(path: str | None) -> list[str]: return [p.lower() for p in Path(path or "").parts]
def _is_protected(path: str | None) -> bool:
    parts = _parts(path)
    if path and Path(path).suffix.lower() in LEDGER_SUFFIXES:
        return True
    return any(p in PROTECTED_NAMES for p in parts) or (parts and parts[-1] in PROTECTED_FILES) or any(m in "\\".join(parts) for m in SYSTEM_MARKERS)
def _is_db(path: str | None) -> bool: return bool(path and Path(path).suffix.lower() in DB_SUFFIXES)

def check_plan(plan: ActionPlan, mode: str = "preview", require_decision_record: bool = True) -> SafetyResult:
    if mode not in {"preview", "execute"}: raise ValueError("mode must be preview or execute")
    blockers, warnings, approvals = [], [], []
    if not plan.approved:
        (blockers if mode == "execute" else warnings).append("Plan is not approved")
    if plan.dry_run:
        (blockers if mode == "execute" else warnings).append("Plan is dry-run")
    if require_decision_record and not plan.metadata.get("decision"):
        (blockers if mode == "execute" else warnings).append("Missing decision record")
    if mode == "execute" and not plan.metadata.get("confirm_execute"):
        blockers.append("Execution requires confirm_execute=true")
    if not plan.metadata.get("explicit_execute"):
        approvals.append("explicit_execute")
    creates = {str(Path(s.destination).resolve()) for s in plan.steps if s.operation == "create_folder" and s.destination}
    for step in plan.steps:
        if step.operation == "delete": blockers.append("Delete is disabled")
        if step.operation not in SUPPORTED_OPERATIONS: blockers.append(f"Unsupported operation: {step.operation}")
        if mode == "execute" and step.operation in GUARDED_NOT_IMPLEMENTED:
            blockers.append(f"{step.operation} is not implemented for execution yet")
        if _is_protected(step.source) or _is_protected(step.destination): blockers.append("Target is protected or system path")
        if (_is_db(step.source) or _is_db(step.destination)) and not step.metadata.get("explicit_database_operation"):
            blockers.append("SQLite/database operation requires explicit approval"); approvals.append("explicit_database_operation")
        if step.operation in {"rename", "move", "copy", "archive", "zip_backup"}:
            if not step.source: blockers.append(f"{step.operation} requires source")
            elif not Path(step.source).exists(): blockers.append(f"Source does not exist: {step.source}")
        if step.operation in {"rename", "move", "copy", "archive", "zip_backup", "write_folderbrain", "create_folder", "link_hub"}:
            if not step.destination and step.operation not in {"protect"}: blockers.append(f"{step.operation} requires destination")
            elif step.destination:
                parent = Path(step.destination).parent.resolve()
                if not parent.exists() and str(parent) not in creates: blockers.append(f"Destination parent does not exist: {parent}")
                if Path(step.destination).exists() and not step.metadata.get("allow_overwrite") and step.operation != "create_folder": blockers.append("Destination exists and overwrite was not approved")
        if step.source and step.destination and Path(step.source).drive.lower() != Path(step.destination).drive.lower() and not step.metadata.get("allow_cross_drive"):
            blockers.append("Cross-drive move/copy requires explicit approval"); approvals.append("explicit_cross_drive_operation")
    return SafetyResult(not blockers, "high" if blockers else ("medium" if approvals or warnings else "low"), sorted(set(blockers)), sorted(set(warnings)), sorted(set(approvals)))
