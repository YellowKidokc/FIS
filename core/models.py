from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Risk = Literal["low", "medium", "high"]
DecisionStatus = Literal["pending", "approved", "rejected", "deferred", "protected"]

@dataclass
class FolderBrain:
    folder_id: str
    folder_path: str
    folder_name: str
    summary: str
    slug: str
    keywords: list[str]
    tags: list[str]
    inventory: dict[str, Any]
    top_extensions: dict[str, int]
    classification: dict[str, Any]
    route: dict[str, Any]
    findings: list[dict[str, Any]]
    actions: dict[str, Any]

@dataclass
class Finding:
    finding_id: str
    engine: str
    finding_type: str
    title: str
    summary: str
    items: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    risk: Risk = "low"
    weight: int = 1
    suggested_actions: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)

@dataclass
class ReviewBlock:
    block_id: str
    block_type: str
    title: str
    summary: str
    weight: int
    risk: Risk
    confidence: float
    item_count: int
    items: list[dict[str, Any]]
    suggested_actions: list[str]
    evidence: dict[str, Any]

@dataclass
class ActionStep:
    operation: str
    source: str | None = None
    destination: str | None = None
    reason: str = ""
    risk: Risk = "low"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class ActionPlan:
    plan_id: str
    source_block_id: str
    dry_run: bool
    approved: bool
    steps: list[ActionStep]
    created_by: str = "river"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class SafetyResult:
    allowed: bool
    risk: Risk
    blockers: list[str]
    warnings: list[str]
    required_approvals: list[str]

@dataclass
class DecisionRecord:
    decision_id: str
    block_id: str
    action: str
    decision: DecisionStatus
    user_note: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

def to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items()}
    return obj
