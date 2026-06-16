from __future__ import annotations
from dataclasses import asdict, is_dataclass
from threading import RLock
from typing import Any

class RuntimeStore:
    """Small in-memory store for the local River FIS server lifecycle."""
    def __init__(self):
        self._lock = RLock()
        self.scans_by_path: dict[str, dict[str, Any]] = {}
        self.folderbrains: dict[str, dict[str, Any]] = {}
        self.review_blocks_by_path: dict[str, list[dict[str, Any]]] = {}
        self.review_blocks_by_id: dict[str, dict[str, Any]] = {}
        self.action_plans: dict[str, Any] = {}
        self.decisions: dict[str, Any] = {}
        self.recipes_by_path: dict[str, list[dict[str, Any]]] = {}
        self.storyboards: dict[str, Any] = {}
        self.last_warnings: list[str] = []
        self.last_errors: list[str] = []

    def _plain(self, value):
        if is_dataclass(value): return asdict(value)
        if isinstance(value, list): return [self._plain(v) for v in value]
        if isinstance(value, dict): return {k: self._plain(v) for k, v in value.items()}
        return value

    def put_scan(self, path: str, result: dict[str, Any]):
        with self._lock:
            self.scans_by_path[path] = result
            brain = result.get("folderbrain") or {}
            if brain:
                self.folderbrains[brain.get("folder_id") or path] = brain
                self.folderbrains[path] = brain
            self.put_review_blocks(path, result.get("review_blocks", []))
            self.last_warnings = list(result.get("warnings", []))
            self.last_errors = list(result.get("errors", []))
        return result

    def get_scan(self, path: str):
        with self._lock: return self.scans_by_path.get(path)

    def put_review_blocks(self, path: str, blocks):
        plain = self._plain(blocks)
        with self._lock:
            self.review_blocks_by_path[path] = plain
            for block in plain:
                self.review_blocks_by_id[block["block_id"]] = block
        return plain

    def get_review_blocks(self, path: str):
        with self._lock: return self.review_blocks_by_path.get(path, [])

    def get_review_block(self, block_id: str):
        with self._lock: return self.review_blocks_by_id.get(block_id)

    def put_action_plan(self, plan):
        with self._lock: self.action_plans[plan.plan_id] = plan
        return plan

    def put_recipe_candidates(self, path: str, recipes):
        plain = self._plain(recipes)
        with self._lock: self.recipes_by_path[path] = plain
        return plain

    def get_recipe_candidates(self, path: str):
        with self._lock: return self.recipes_by_path.get(path, [])

    def put_storyboard(self, storyboard):
        storyboard_id = getattr(storyboard, "storyboard_id", None) or storyboard.get("storyboard_id")
        with self._lock: self.storyboards[storyboard_id] = storyboard
        return storyboard

    def get_storyboard(self, storyboard_id: str):
        with self._lock: return self.storyboards.get(storyboard_id)

    def link_storyboard_to_action_plan(self, storyboard_id: str, plan_id: str):
        with self._lock:
            story = self.storyboards.get(storyboard_id)
            if story is None: return None
            if hasattr(story, "linked_action_plan_id"):
                story.linked_action_plan_id = plan_id
            elif isinstance(story, dict):
                story["linked_action_plan_id"] = plan_id
            return story

    def get_action_plan(self, plan_id: str):
        with self._lock: return self.action_plans.get(plan_id)

    def update_action_plan(self, plan):
        return self.put_action_plan(plan)

    def put_decision(self, decision):
        decision_id = getattr(decision, "decision_id", None) or (decision.get("decision_id") if isinstance(decision, dict) else None)
        if not decision_id:
            decision_id = f"decision_{len(self.decisions)+1:05d}"
        with self._lock: self.decisions[decision_id] = decision
        return decision

    def get_decisions(self, path: str | None = None):
        with self._lock:
            values = list(self.decisions.values())
        if not path: return values
        return [d for d in values if getattr(d, "payload", {}).get("path") == path or (isinstance(d, dict) and d.get("path") == path)]

    def status(self):
        with self._lock:
            return {"scans": len(self.scans_by_path), "folderbrains": len(self.folderbrains), "review_blocks": len(self.review_blocks_by_id), "action_plans": len(self.action_plans), "decisions": len(self.decisions), "recipes": sum(len(v) for v in self.recipes_by_path.values()), "storyboards": len(self.storyboards), "warnings": self.last_warnings, "errors": self.last_errors}

runtime_store = RuntimeStore()
