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


def test_ui_has_exact_production_modes():
    expected = ["Home / Story", "Intelligence", "Advanced", "Plans / History", "Diagnostics"]
    for label in expected:
        assert label in HTML
    assert "Settings / Diagnostics" not in HTML


def test_advanced_does_not_direct_execute():
    advanced = HTML.split('<section id="advanced"', 1)[1].split('<section id="plans"', 1)[0]
    assert "executeApproved" not in advanced
    assert "Advanced creates dry-run plans only" in advanced
