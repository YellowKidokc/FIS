from __future__ import annotations
import re
from pathlib import Path
from core.models import Finding
try:
    from naming_engine import NamingEngine, PRESETS, slugify
except Exception:
    NamingEngine = None; PRESETS = {}; slugify = lambda text, **_: re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "file"

UUID_RE = re.compile(r"[a-f0-9]{8,}(-[a-f0-9]{4,}){0,4}", re.I)
SCREENSHOT_RE = re.compile(r"^(screenshot|screen shot|img_|image|pxl_|dsc_)", re.I)
RESIDUE_RE = re.compile(r"(\(\d+\)|copy|download|untitled|new document|final_final)", re.I)
BAD_SEP_RE = re.compile(r"(__+|--+|\s{2,}|[ _.-]{3,})")

def _reasons(name: str) -> list[str]:
    stem = Path(name).stem
    reasons = []
    if UUID_RE.search(stem): reasons.append("hash_or_uuid_like")
    if SCREENSHOT_RE.search(stem): reasons.append("screenshot_or_camera_name")
    if RESIDUE_RE.search(stem): reasons.append("download_or_copy_residue")
    if BAD_SEP_RE.search(stem): reasons.append("repeated_bad_separators")
    if stem.isupper() and len(stem) > 8: reasons.append("all_caps")
    if len(stem) <= 3 or stem.lower() in {"untitled", "new", "file"}: reasons.append("weak_generated_name")
    return reasons

def _candidate_name(item: dict, folderbrain) -> str:
    keywords = [k for k in folderbrain.keywords if k and k != "[none]"] or [folderbrain.folder_name]
    base = slugify(" ".join(keywords[:3]))
    suffix = slugify(Path(item["name"]).stem)[:32]
    ext = item.get("ext") or Path(item["name"]).suffix.lower()
    return f"{base}-{suffix}{ext}" if suffix else f"{base}{ext}"

def analyze(folderbrain, cache=None, options=None):
    candidates = []
    for item in folderbrain.inventory.get("files", []):
        reasons = _reasons(item.get("name", ""))
        if reasons:
            candidates.append({**item, "reasons": reasons, "proposed_name": _candidate_name(item, folderbrain), "proposed_scheme": "folder-keywords + cleaned-original"})
    if not candidates: return []
    return [Finding("rename_candidates_001", "naming", "rename_candidates", "Rename candidates found", "Some filenames look generated, duplicated, residue-like, or hard to understand. River can preview safer names without renaming directly.", items=candidates[:100], confidence=0.78, risk="medium", weight=8, suggested_actions=["preview_names", "edit_pattern", "approve_rename_plan"], evidence={"preset_count": len(PRESETS), "rules": ["uuid", "screenshot", "residue", "bad_separator", "all_caps", "weak"]})]
