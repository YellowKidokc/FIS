from __future__ import annotations
from core.models import Finding
from engines.fingerprint import normalized_name

def analyze(folderbrain, cache=None, options=None):
    folders = folderbrain.inventory.get("folders", [])
    groups = {}
    for folder in folders:
        key = normalized_name(folder.get("name", ""))
        if key: groups.setdefault(key, []).append(folder)
    similar = [v for v in groups.values() if len(v) > 1]
    if not similar: return []
    return [Finding("similar_hub_001", "similarity", "similar_hub", "Similar folder hubs found", "Some folders have similar names and may be related; link or hub them before moving anything.", items=[{"folders": g} for g in similar], confidence=0.72, risk="low", weight=6, suggested_actions=["find_similar", "create_hub_page", "link_dont_move"], evidence={"method": "normalized_folder_name"})]
