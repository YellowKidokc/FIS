from __future__ import annotations
import json, shutil, zipfile
from pathlib import Path
from core.models import ActionPlan
from core.safety import check_plan

def preview_plan(plan: ActionPlan) -> dict:
    return {"plan_id": plan.plan_id, "dry_run": True, "steps": [step.__dict__ for step in plan.steps]}

def execute_plan(plan: ActionPlan) -> dict:
    safety = check_plan(plan)
    if not safety.allowed:
        return {"executed": False, "safety": safety.__dict__, "log": []}
    log = []
    for step in plan.steps:
        log.append({"before": step.__dict__})
        src = Path(step.source) if step.source else None
        dst = Path(step.destination) if step.destination else None
        if step.operation == "create_folder" and dst: dst.mkdir(parents=True, exist_ok=True)
        elif step.operation in {"rename", "move", "archive"} and src and dst:
            dst.parent.mkdir(parents=True, exist_ok=True); shutil.move(str(src), str(dst))
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
        log[-1]["after"] = "ok"
    return {"executed": True, "log": log}

def rollback_plan(plan_id: str) -> dict:
    return {"plan_id": plan_id, "supported": False, "message": "rollback metadata will be implemented after execution logging is finalized"}
