"""Shared preview-first action-plan schema for River FIS."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any
from uuid import uuid4

ACTION_TYPES = {
    "rename", "move", "copy", "create_folder", "deduplicate", "recycle",
    "archive", "split", "merge", "tag", "report", "skip",
}
SAFETY_LEVELS = {"preview_only", "safe", "review_required", "blocked"}


@dataclass
class Action:
    type: str
    scope: dict[str, Any] = field(default_factory=dict)
    parameters: dict[str, Any] = field(default_factory=dict)
    safety: str = "preview_only"
    reason: str = ""
    requires_approval: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_action(action_type: str, **kwargs: Any) -> dict[str, Any]:
    if action_type not in ACTION_TYPES:
        raise ValueError(f"Unsupported action type: {action_type}")
    safety = kwargs.get("safety", "preview_only")
    if safety not in SAFETY_LEVELS:
        raise ValueError(f"Unsupported safety level: {safety}")
    return Action(type=action_type, **kwargs).to_dict()
