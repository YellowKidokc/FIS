import re
from pathlib import Path
from app.server import ROUTES

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "ui" / "index.html").read_text(encoding="utf-8")

def test_ui_index_exists():
    assert (ROOT / "ui" / "index.html").exists()

def test_ui_references_existing_css():
    for href in re.findall(r'<link[^>]+href="([^"]+)"', HTML):
        if href.startswith("http"):
            continue
        assert (ROOT / href.lstrip("/")).exists(), href

def test_ui_fetch_endpoints_are_registered():
    registered = {route for routes in ROUTES.values() for route in routes}
    for endpoint in re.findall(r"(?:fetch|apiFetch|post)\(\s*['\"]([^'\"]+)", HTML):
        base = endpoint.split("?")[0]
        if base.startswith("/api/"):
            assert base in registered, base

def test_ui_modes_present():
    for label in ["Home / Story", "Intelligence", "Advanced", "Plans / History", "Settings / Diagnostics"]:
        assert label in HTML

