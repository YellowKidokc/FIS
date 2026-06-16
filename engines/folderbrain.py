from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from typing import Any
from core.models import FolderBrain

DOMAIN_EXTENSIONS = {"code": {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml", ".yml"}, "documents": {".txt", ".md", ".pdf", ".doc", ".docx", ".rtf"}, "data": {".csv", ".tsv", ".xls", ".xlsx", ".db", ".sqlite"}, "media": {".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".wav"}}

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "folder"

def classify_inventory(inventory: dict[str, Any]) -> dict[str, Any]:
    counts = inventory.get("extension_counts") or inventory.get("top_extensions") or {}
    total = max(sum(counts.values()), 1)
    scores = {domain: sum(counts.get(ext, 0) for ext in exts) for domain, exts in DOMAIN_EXTENSIONS.items()}
    dominant = max(scores, key=scores.get) if scores else "mixed"
    confidence = round((scores.get(dominant, 0) / total) * 100, 2)
    if confidence < 35:
        dominant, confidence = "mixed", max(confidence, 25)
    return {"domain": dominant, "confidence": confidence, "needs_review": confidence < 75, "dominant_domains": sorted(scores.items(), key=lambda x: x[1], reverse=True)}

def build(folder_path: str, cache=None, inventory: dict | None = None) -> FolderBrain:
    path = Path(folder_path).expanduser().resolve()
    inv = inventory or (cache.get("inventory") if isinstance(cache, dict) else {}) or {}
    classification = classify_inventory(inv)
    confidence = classification["confidence"]
    route = {"keep_in_place": confidence < 75, "move_as_unit": confidence >= 75, "split_recommended": False, "recommendation": "keep in place until review complete" if confidence < 75 else "review move-as-unit option"}
    keywords = [path.name, *[k.strip(".") for k in list((inv.get("top_extensions") or {}).keys())[:5] if k != "[none]"]]
    actions = {"write_folderbrain": "requires action plan approval", "move_or_rename": "requires review decision, safety, executor"}
    extra = {"schema": "river.folderbrain.v1", "root": str(path), "state": "review", "dominant_domains": classification["dominant_domains"], "history": [], "needs_review": classification["needs_review"]}
    brain = FolderBrain(folder_id=hashlib.sha1(str(path).encode()).hexdigest()[:12], folder_path=str(path), folder_name=path.name, summary=f"{path.name} contains {inv.get('file_count', 0)} files, {inv.get('folder_count', 0)} folders, and {inv.get('total_size', 0)} bytes.", slug=slugify(path.name), keywords=keywords, tags=[], inventory=inv, top_extensions=inv.get("top_extensions", {}), classification=classification, route=route, findings=[], actions=actions)
    setattr(brain, "extra", extra)
    return brain

def to_payload(brain: FolderBrain) -> dict[str, Any]:
    data = brain.__dict__.copy()
    data.update(data.pop("extra", {}))
    return data

def write(folderbrain: FolderBrain, destination: str | None = None) -> Path:
    target = Path(destination or Path(folderbrain.folder_path) / ".folderbrain.json")
    target.write_text(json.dumps(to_payload(folderbrain), indent=2), encoding="utf-8")
    return target
