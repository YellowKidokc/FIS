from __future__ import annotations
from core.models import Finding

def analyze(folderbrain, cache=None, options=None):
    classification = folderbrain.classification or {}
    confidence = float(classification.get("confidence", 0))
    needs_review = confidence < 75
    rec = {"keep_in_place": needs_review, "move_as_unit": not needs_review, "split_by_theme": False, "create_hub": False, "archive_review": bool(folderbrain.inventory.get("large_files") or folderbrain.inventory.get("tiny_folders")), "needs_review": needs_review, "recommendation": "Recommended: keep in place until review complete." if needs_review else "Move-as-unit can be reviewed, never automatic."}
    folderbrain.route.update(rec)
    return [Finding("route_001", "router", "route_recommendation", "Move / keep decision", rec["recommendation"], confidence=0.8 if not needs_review else 0.55, risk="medium" if needs_review else "low", weight=8 if needs_review else 6, suggested_actions=["keep_in_place", "move_as_unit", "split_by_theme", "create_hub", "archive_review"], evidence=rec)]
