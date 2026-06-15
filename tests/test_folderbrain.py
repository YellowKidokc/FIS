from engines.inventory import scan
from engines.folderbrain import build


def test_folderbrain_returns_json_ready_model(tmp_path):
    (tmp_path / "a.txt").write_text("hello")
    inv = scan(str(tmp_path))
    brain = build(str(tmp_path), {"inventory": inv}, inv)
    assert brain.folder_path == str(tmp_path.resolve())
    assert brain.inventory["file_count"] == 1
