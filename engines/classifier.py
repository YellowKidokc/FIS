from core.models import Finding

def analyze(folderbrain, cache=None, options=None):
    top = folderbrain.top_extensions
    if not top: return []
    domain = "code" if any(ext in top for ext in [".py", ".js", ".jsx", ".html"]) else "mixed"
    return [Finding("classify_001", "classifier", "classification", "Classification review", f"Folder appears to be {domain} based on extension mix.", confidence=0.65, risk="low", weight=7, suggested_actions=["accept_domain", "choose_different_domain", "split_by_theme"], evidence={"top_extensions": top})]
