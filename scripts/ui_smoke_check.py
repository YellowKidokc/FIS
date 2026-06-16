from __future__ import annotations
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.server import ROUTES
ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "ui" / "index.html"
errors = []
def fail(msg): errors.append(msg)
if not INDEX.exists(): fail("ui/index.html is missing")
html = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
for href in re.findall(r'<link[^>]+href="([^"]+)"', html):
    if href.startswith("http"): continue
    local = ROOT / href.lstrip("/")
    if not local.exists(): fail(f"missing css/script reference: {href}")
fetches_get = set(re.findall(r"apiFetch\(\s*['\"]([ ^'\"]+)", html))
fetches_post = set(re.findall(r"post\(\s*['\"]([ ^'\"]+)", html))
registered_get = set(ROUTES.get("GET", []))
registered_post = set(ROUTES.get("POST", []))
for f in fetches_get:
    base = f.split("?")[0]
    if base.startswith("/api/") and base not in registered_get:
        fail(f"GET fetch endpoint not registered: {base}")
for f in fetches_post:
    base = f.split("?")[0]
    if base.startswith("/api/") and base not in registered_post:
        fail(f"POST fetch endpoint not registered: {base}")
required = {"/api/health","/api/cache/status","/api/scan","/api/folderbrain","/api/review/blocks","/api/recipes","/api/recipes/next","/api/storyboard/build","/api/storyboard","/api/storyboard/decision","/api/action/plan","/api/action/preview","/api/action/approve","/api/action/execute","/api/preferences/record","/api/preferences/stats"}
for r in required:
    if r not in html: fail(f"required production endpoint not referenced: {r}")
handlers = set(re.findall(r"onclick=\"([a-zA-Z_$][\w$]*)\(", html)) | set(re.findall(r"onclick='([a-zA-Z_$][\w$]*)\(", html))
for h in handlers:
    if not re.search(rf"function\s+{re.escape(h)}\s*\(", html): fail(f"onclick handler missing function: {h}")
for mode in ["Home / Story","Intelligence","Advanced","Plans / History","Diagnostics"]:
    if mode not in html: fail(f"missing mode label: {mode}")
if errors:
    print("UI smoke check failed:")
    for e in errors: print("-", e)
    sys.exit(1)
print("UI smoke check passed")
