from pathlib import Path

def test_purge_plan_exists():
    text = Path("docs/PURGE_PLAN.md").read_text(encoding="utf-8")
    for section in ["KEEP_ACTIVE", "LEGACY_KEEP", "ARCHIVE_AFTER_TESTS", "DELETE_GENERATED", "DELETE_DUPLICATE", "UNKNOWN_REVIEW"]:
        assert section in text
