from __future__ import annotations
from uuid import uuid4
from .action_schema import make_action
from .safety_rules import validate_plan
from .scan_summary import get_scan

PLANS: dict[str, dict] = {}

TITLES = ["Clean obvious duplicates safely", "Move uncertainty into review", "Create a report-only cleanup map"]
UNDERSTOOD = [
    ["Keep newest exact duplicate by default", "Move uncertain items to review", "Skip protected files"],
    ["Avoid recycling by default", "Group unresolved duplicates for review", "Protect projects/configs/index files"],
    ["Make no filesystem changes", "Produce a preview/report first", "Leave all unknowns untouched"],
]


def build_simple_plan(scan_id: str, stage: str = "file_cleaner", attempt: int = 1, previous_rejections=None) -> dict:
    scan = get_scan(scan_id)
    if not scan:
        raise KeyError(scan_id)
    idx = max(0, min(2, int(attempt or 1) - 1))
    actions = [
        make_action("deduplicate", scope={"duplicate_groups": "exact_hash", "protected": False}, parameters={"keeper": "newest", "extras": "review", "rollback_supported": True}, reason="Exact duplicate extras are candidates only; never delete every group member."),
        make_action("skip", scope={"protected_items": True}, reason="Protected files are never changed by FIS simple mode"),
    ] if idx == 0 else [
        make_action("move", scope={"items": "uncertain_or_duplicate_extras", "protected": False}, parameters={"destination": "_review/fis", "rollback_supported": True}, reason="Rejected safer recycling; collect review candidates instead."),
        make_action("skip", scope={"unknown_items": True}, reason="Unknown/low-confidence files require review"),
    ] if idx == 1 else [
        make_action("report", scope={"scan_id": scan_id}, parameters={"format": "preview_rows"}, reason="Final simple option is report-only."),
        make_action("skip", scope={"protected_items": True}, reason="No changes in report-only option"),
    ]
    preview = []
    for group in scan["findings"].get("duplicates", [])[:10]:
        paths = group.get("paths", [])
        if len(paths) > 1:
            preview.append({"before": paths[1], "after": "_review/duplicates/" + paths[1].split('/')[-1].split('\\')[-1], "reason": "duplicate extra preview"})
    plan = {"plan_id": str(uuid4()), "mode": "file_intelligence_system", "stage": stage, "attempt": idx + 1, "title": TITLES[idx], "understood": UNDERSTOOD[idx], "actions": actions, "warnings": [], "preview": preview, "safety": "preview_only", "requires_user_approval": True}
    plan = validate_plan(plan, plan["mode"])
    PLANS[plan["plan_id"]] = plan
    return plan
