from core.models import Finding, FolderBrain
from core.review_blocks import build


def brain():
    return FolderBrain("id", "/tmp/root", "root", "summary", "root", [], [], {}, {}, {}, {}, [], {})


def test_tiny_folder_finding_becomes_review_block():
    blocks = build(brain(), [Finding("f1", "inventory", "tiny_folder", "Tiny", "Tiny folders", items=[{"path":"a"}], confidence=0.8, risk="medium", weight=5)])
    tiny = next(b for b in blocks if b.block_type == "tiny_folder")
    assert tiny.title == "Tiny Folder Review"
    assert "archive_empty" in tiny.suggested_actions


def test_duplicate_finding_becomes_duplicate_review_block():
    blocks = build(brain(), [Finding("f1", "duplicates", "exact_duplicate", "Dupes", "Duplicate files", confidence=0.99, risk="medium", weight=9)])
    dupes = next(b for b in blocks if b.block_type == "duplicates")
    assert dupes.weight == 9
