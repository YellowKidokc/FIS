from core.models import Finding
try:
    from naming_engine import NamingEngine, clean_filename, PRESETS, slugify
except Exception:  # noqa: BLE001
    NamingEngine = None; PRESETS = {}; clean_filename = lambda name: name; slugify = lambda text, **_: text

def analyze(folderbrain, cache=None, options=None):
    files = folderbrain.inventory.get("files", [])
    bad = [f for f in files if " " in f.get("name", "") or any(ch.isupper() for ch in f.get("name", ""))][:25]
    if not bad: return []
    return [Finding("rename_bad_names_001", "naming", "rename", "Rename scheme preview", "Some filenames could be normalized with a preview-only naming plan.", items=bad, confidence=0.75, risk="medium", weight=8, suggested_actions=["preview_names", "edit_pattern", "approve_rename_plan"], evidence={"preset_count": len(PRESETS)})]
