"""Safety validator for preview-only File Intelligence System plans."""
from __future__ import annotations

PROTECTED_EXTENSIONS = {
    ".exe", ".dll", ".so", ".dylib", ".sys", ".bat", ".cmd", ".ps1",
    ".ini", ".cfg", ".conf", ".toml", ".yaml", ".yml", ".json", ".xml",
    ".db", ".sqlite", ".sqlite3", ".idx", ".map", ".lock",
}
PROTECTED_NAMES = {
    ".git", ".svn", ".hg", "node_modules", ".venv", "venv", "package.json",
    "pyproject.toml", "requirements.txt", "workspace.code-workspace",
}


def is_protected(path: str) -> bool:
    import os
    p = path.lower()
    name = os.path.basename(p)
    _, ext = os.path.splitext(name)
    return name in PROTECTED_NAMES or ext in PROTECTED_EXTENSIONS or "/.git/" in p or "\\.git\\" in p


def validate_plan(plan: dict, mode: str = "file_intelligence_system") -> dict:
    warnings = list(plan.get("warnings", []))
    blocked = []
    for action in plan.get("actions", []):
        action_type = action.get("type")
        safety = action.get("safety")
        scope = action.get("scope", {})
        if action_type == "delete":
            blocked.append("Permanent delete is never allowed; use recycle or review.")
            action["type"] = "recycle"
            action["safety"] = "blocked"
        if action_type in {"move", "rename", "recycle", "deduplicate"} and mode.startswith("file_intelligence_system"):
            if scope in ("protected_items", "unknown_items") or (isinstance(scope, dict) and scope.get("protected")):
                blocked.append("Protected or low-confidence items cannot be changed in File Intelligence System mode.")
                action["safety"] = "blocked"
        if action_type in {"recycle", "archive", "deduplicate"}:
            action["requires_approval"] = True
            if not action.get("parameters", {}).get("rollback_supported", True):
                blocked.append("Destructive action lacks rollback support.")
                action["safety"] = "blocked"
        if action_type == "merge" and not action.get("parameters", {}).get("advanced_explicit_conflict_handling"):
            blocked.append("Same-name/different-content merge requires Advanced Workbench handling.")
            action["safety"] = "blocked"
    if blocked:
        warnings.extend(blocked)
    plan["warnings"] = warnings
    plan["safety"] = "preview_only"
    plan["requires_user_approval"] = True
    return plan
