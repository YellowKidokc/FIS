from core.orchestrator import run_folder_intelligence
from core.recipes import build_recipe_candidates


def make_sample(tmp_path):
    root = tmp_path / "sample"; root.mkdir()
    (root / "report.txt").write_text("same")
    (root / "report copy.txt").write_text("same")
    (root / "badname_A79A36A1.txt").write_text("bad")
    (root / "tiny").mkdir(); (root / "tiny" / "lone.txt").write_text("one")
    return root


def types_for(root):
    result = run_folder_intelligence(str(root))
    return [r.recipe_type for r in build_recipe_candidates(result, str(root))]


def test_exact_duplicates_create_clean_duplicates_recipe(tmp_path):
    assert "clean_duplicates" in types_for(make_sample(tmp_path))


def test_rename_findings_create_clean_names_recipe(tmp_path):
    assert "clean_names" in types_for(make_sample(tmp_path))


def test_low_confidence_creates_review_low_confidence_recipe(tmp_path):
    assert "review_low_confidence" in types_for(make_sample(tmp_path))


def test_tiny_folder_or_composition_creates_sort_recipe(tmp_path):
    assert "sort_by_composition" in types_for(make_sample(tmp_path))

