from __future__ import annotations
import re
from collections import Counter
from core.models import Finding
from engines.folderbrain import DOMAIN_EXTENSIONS
KEYWORDS = {"finance": ["candle", "trade", "trading", "market", "stock", "forex", "crypto"], "course": ["course", "lesson", "module", "training"], "code": ["src", "app", "component", "server", "api"], "documents": ["report", "doc", "readme", "notes"]}

def classify(folderbrain) -> dict:
    ext_counts = folderbrain.inventory.get("extension_counts", {})
    total = max(sum(ext_counts.values()), 1)
    scores = Counter()
    for domain, exts in DOMAIN_EXTENSIONS.items():
        scores[domain] += sum(ext_counts.get(ext, 0) for ext in exts) * 3
    text = " ".join([folderbrain.folder_name, *[f.get("name", "") for f in folderbrain.inventory.get("files", [])[:200]]]).lower()
    for domain, words in KEYWORDS.items():
        scores[domain] += sum(len(re.findall(rf"\b{re.escape(w)}\b", text)) for w in words)
    domain, score = scores.most_common(1)[0] if scores else ("mixed", 0)
    confidence = round(min(95, max(20, (score / (total * 5)) * 100)), 2)
    if confidence < 35: domain = "mixed"
    return {"domain": domain, "confidence": confidence, "needs_review": confidence < 75, "scores": dict(scores)}

def analyze(folderbrain, cache=None, options=None):
    result = classify(folderbrain)
    folderbrain.classification.update(result)
    return [Finding("classify_001", "classifier", "classification", "Classification review", f"Folder appears to be {result['domain']} with {result['confidence']}% confidence.", confidence=result["confidence"] / 100, risk="medium" if result["needs_review"] else "low", weight=7, suggested_actions=["accept_domain", "choose_different_domain", "split_by_theme"], evidence=result)]
