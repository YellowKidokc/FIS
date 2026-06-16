from __future__ import annotations
import json, shutil, zipfile
from datetime import datetime
from pathlib import Path
from core.models import ActionPlan
from core.safety import check_plan

EXECUTABLE_NOW = {"create_folder", "write_folderbrain", "copy", "zip_backup", "protect", "link_hub"}

def _entry(plan: ActionPlan, idx: int, step, status: str, error: str = "") -> dict:
    return {"plan_id": plan.plan_id, "step_index": idx, "operation": step.operation, "source": step.source, "destination": step.destination, "status": status, "error": error, "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z"}

def preview_plan(plan: ActionPlan) -> dict:
    return {"plan_id": plan.plan_id, "dry_run": True, "safety": check_plan(plan, mode="preview").__dict__, "steps": [step.__dict__ for step in plan.steps]}

def execute_plan(plan: ActionPlan) -> dict:
    safety = check_plan(plan, mode="execute")
    if not safety.allowed:
        return {"executed": False, "safety": safety.__dict__, "log": []}
    log = []
    for idx, step in enumerate(plan.steps):
        if step.operation not in EXECUTABLE_NOW:
            log.append(_entry(plan, idx, step, "not_implemented", f"{step.operation} is not enabled for execution yet")); continue
        src = Path(step.source) if step.source else None; dst = Path(step.destination) if step.destination else None
        try:
            if step.operation == "create_folder" and dst:
                dst.mkdir(parents=True, exist_ok=True)
            elif step.operation == "copy" and src and dst:
                dst.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, dst)
            elif step.operation == "write_folderbrain" and dst:
                dst.write_text(json.dumps(step.metadata.get("folderbrain", {}), indent=2), encoding="utf-8")
            elif step.operation == "zip_backup" and src and dst:
                with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
                    if src.is_dir():
                        for p in src.rglob("*"):
                            if p.is_file(): zf.write(p, p.relative_to(src))
                    else: zf.write(src, src.name)
            elif step.operation == "link_hub" and dst:
                dst.write_text(f"# River Hub\n\nSource: `{step.source}`\n", encoding="utf-8")
            elif step.operation == "protect":
                pass
            log.append(_entry(plan, idx, step, "ok"))
        except Exception as exc:
            log.append(_entry(plan, idx, step, "error", str(exc)))
            return {"executed": False, "safety": safety.__dict__, "log": log}
    return {"executed": all(row["status"] == "ok" for row in log), "safety": safety.__dict__, "log": log}

def rollback_plan(plan_id: str) -> dict:
    return {"plan_id": plan_id, "supported": False, "message": "rollback metadata will be implemented after execution logging is finalized"}
