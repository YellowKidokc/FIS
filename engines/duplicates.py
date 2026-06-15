from __future__ import annotations
import hashlib
from collections import defaultdict
from pathlib import Path
from core.models import Finding

def _hash(path: str) -> str | None:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None

def analyze(folderbrain, cache=None, options=None) -> list[Finding]:
    inventory = folderbrain.inventory if hasattr(folderbrain, "inventory") else {}
    groups = defaultdict(list)
    for item in inventory.get("files", [])[: int((options or {}).get("max_hash_files", 1000))]:
        digest = _hash(item["path"])
        if digest: groups[digest].append(item)
    dupes = [v for v in groups.values() if len(v) > 1]
    if not dupes: return []
    return [Finding("dup_exact_001", "duplicates", "exact_duplicate", "Exact duplicate files found", "Files with identical SHA-256 hashes need review before archiving extras.", items=[{"files": g} for g in dupes], confidence=0.99, risk="medium", weight=9, suggested_actions=["review_duplicates", "archive_extra_copy", "ignore_group"], evidence={"method": "sha256"})]
