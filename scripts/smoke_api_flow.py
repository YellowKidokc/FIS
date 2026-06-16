from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.action_plans import create_plan, approve_plan, executable_copy
from core.executor import preview_plan, execute_plan
from core.models import DecisionRecord, ReviewBlock
from core.orchestrator import run_folder_intelligence
from core.runtime_store import RuntimeStore

def line(label: str, status: str, extra: str = ""):
    print(f"{label}: {status}{(' - ' + extra) if extra else ''}")

def main() -> int:
    store = RuntimeStore()
    with tempfile.TemporaryDirectory(prefix="river_fis_smoke_") as tmp:
        root = Path(tmp) / "sample"; root.mkdir()
        (root / "report.txt").write_text("same")
        (root / "report copy.txt").write_text("same")
        (root / "badname_A79A36A1.txt").write_text("bad")
        (root / "tiny").mkdir(); (root / "tiny" / "lone.txt").write_text("one")
        line("HEALTH", "ok")
        result = run_folder_intelligence(str(root)); store.put_scan(str(root), result)
        line("SCAN", "ok" if result.get("folderbrain") else "fail")
        line("FOLDERBRAIN", "ok" if result.get("folderbrain") else "fail", result.get("folderbrain", {}).get("summary", ""))
        blocks = result.get("review_blocks", [])
        line("REVIEW BLOCKS", "ok" if blocks else "fail", str(len(blocks)))
        block = ReviewBlock(**next((b for b in blocks if b["block_type"] == "folder_template"), blocks[0]))
        decision = DecisionRecord("smoke_decision", block.block_id, "create_missing_folders", "approved", payload={"path": str(root)})
        plan = create_plan(block, decision, action="create_missing_folders", folder_path=str(root), payload={"folders": ["smoke_created"]}); store.put_action_plan(plan)
        line("ACTION PLAN", "dry-run" if plan.dry_run and not plan.approved else "unexpected", plan.plan_id)
        preview = preview_plan(plan)
        line("PREVIEW", "ok" if preview["safety"] else "fail")
        approved = approve_plan(plan, True); store.update_action_plan(approved)
        line("APPROVE", "ok" if approved.approved and approved.dry_run else "fail")
        attempted = execute_plan(executable_copy(approved, True))
        line("EXECUTE", "safe-completed" if attempted["executed"] else "blocked", json.dumps(attempted["safety"]))
    return 0
if __name__ == "__main__": raise SystemExit(main())
