from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from collections import Counter
from core.action_plans import create_plan
from core.executor import preview_plan
from core.models import DecisionRecord, ReviewBlock
from core.orchestrator import run_folder_intelligence

def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: python scripts/diagnose_pipeline.py "C:\\path\\to\\test\\folder"')
        return 2
    result = run_folder_intelligence(sys.argv[1])
    if result.get("error"):
        print(result["error"]); return 1
    brain = result["folderbrain"]; inv = brain["inventory"]
    print("FolderBrain summary:", brain["summary"])
    print("Inventory counts:", json.dumps({"files": inv.get("file_count"), "folders": inv.get("folder_count"), "bytes": inv.get("total_size")}, indent=2))
    print("Finding counts by type:", dict(Counter(f["finding_type"] for f in result["findings"])))
    print("Review block counts:", len(result["review_blocks"]))
    print("Top 5 review blocks:")
    for block in result["review_blocks"][:5]:
        print(f"- {block['title']} ({block['block_type']}): items={block['item_count']} risk={block['risk']} weight={block['weight']}")
    sample_block = ReviewBlock(**result["review_blocks"][0])
    plan = create_plan(sample_block, DecisionRecord("diagnose", sample_block.block_id, "review", "approved"), action="review", folder_path=sys.argv[1])
    print("Sample dry-run safety:", json.dumps(preview_plan(plan)["safety"], indent=2))
    return 0
if __name__ == "__main__": raise SystemExit(main())
