from __future__ import annotations
import hashlib, json, re
from pathlib import Path
from core.models import FolderBrain

def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "folder"

def build(folder_path: str, cache=None, inventory: dict | None = None) -> FolderBrain:
    path = Path(folder_path).expanduser().resolve()
    inv = inventory or (cache.get("inventory") if isinstance(cache, dict) else {}) or {}
    folder_id = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:12]
    top = inv.get("top_extensions", {})
    keywords = [path.name, *[k.strip(".") for k in list(top)[:5] if k != "[none]"]]
    return FolderBrain(folder_id=folder_id, folder_path=str(path), folder_name=path.name, summary=f"{path.name} contains {inv.get('file_count', 0)} files across {inv.get('folder_count', 0)} folders.", slug=_slug(path.name), keywords=keywords, tags=[], inventory=inv, top_extensions=top, classification={}, route={}, findings=[], actions={})

def write(folderbrain: FolderBrain, destination: str | None = None) -> Path:
    target = Path(destination or Path(folderbrain.folder_path) / ".folderbrain.json")
    target.write_text(json.dumps(folderbrain.__dict__, indent=2), encoding="utf-8")
    return target
