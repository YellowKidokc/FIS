from __future__ import annotations
from uuid import uuid4
from .action_schema import make_action
from .safety_rules import validate_plan
from .scan_summary import get_scan
from .simple_strategies import PLANS


def build_custom_plan(scan_id: str, stage: str, user_request: str, previous_rejections=None) -> dict:
    if not get_scan(scan_id):
        raise KeyError(scan_id)
    text = (user_request or "").lower()
    understood = ["Convert plain-English intent into a preview-only plan", "Skip protected project/config/index/program files"]
    actions = []
    if "do not delete" in text or "don't delete" in text or "no delete" in text:
        understood.insert(0, "Do not delete or recycle anything")
    if "duplicate" in text:
        understood.append("Move duplicate extras to review")
        actions.append(make_action("move", scope={"duplicate_nonkeepers": True, "protected": False}, parameters={"destination": "_review/duplicates", "rollback_supported": True}, safety="preview_only", reason="User asked to handle duplicates without direct execution."))
    if "html" in text:
        understood.append("Group HTML files only when not part of protected projects")
        actions.append(make_action("move", scope={"extension": ".html", "protected": False}, parameters={"destination": "_review/html", "rollback_supported": True}, safety="preview_only", reason="HTML grouping is preview-only and excludes project roots/configs."))
    if "empty" in text or "flatten" in text:
        understood.append("Flatten empty folder nests only; preserve real projects")
        actions.append(make_action("report", scope={"empty_folder_nests": True}, parameters={}, reason="Folder flattening starts as a report to avoid damaging projects."))
    actions.append(make_action("skip", scope={"protected_items": True}, reason="Protected items are never changed by FIS simple mode"))
    if len(actions) == 1:
        actions.insert(0, make_action("report", scope={"scan_id": scan_id}, reason="Request needs clarification; report current findings first."))
    plan = {"plan_id": str(uuid4()), "mode": "file_intelligence_system_custom", "stage": stage, "status": "preview_only", "understood": understood, "actions": actions, "warnings": [], "preview": [], "requires_user_approval": True}
    plan = validate_plan(plan, plan["mode"])
    PLANS[plan["plan_id"]] = plan
    return plan
