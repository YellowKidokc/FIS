"""Unit tests for exporter/processor.py."""

import os
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from exporter.processor import (
    _build_output,
    _collect_files,
    _generate_structure_with_depth,
    _generate_structure_with_empty_dirs,
    _load_gitignore_spec,
    build_full_output,
    detect_language,
    export_project,
    generate_project_structure,
    handle_clipboard_copy,
    read_file_content,
)


# ---------------------------------------------------------------------------
# _load_gitignore_spec
# ---------------------------------------------------------------------------
class TestLoadGitignoreSpec:
    def test_gitignore_not_found(self, tmp_path: Path) -> None:
        """No .gitignore file -> None."""
        root = tmp_path / "no_git"
        root.mkdir()
        result = _load_gitignore_spec(root)
        assert result is None, "Expected None when .gitignore missing"

    def test_gitignore_exists(self, tmp_path: Path) -> None:
        """Valid .gitignore -> PathSpec object."""
        root = tmp_path / "with_git"
        root.mkdir()
        (root / ".gitignore").write_text("*.log\n/dist/\n")
        spec = _load_gitignore_spec(root)
        assert spec is not None, "Expected PathSpec instance"
        # Check that patterns are loaded (mock would be too tight; trust pathspec)

    def test_read_oserror_returns_none(self, tmp_path: Path) -> None:
        """OSError during .gitignore read -> None."""
        root = tmp_path / "bad_git"
        root.mkdir()
        git_file = root / ".gitignore"
        git_file.write_text("ignore")
        with patch.object(Path, "read_text", side_effect=OSError("permission")):
            result = _load_gitignore_spec(root)
            assert result is None, "OSError should yield None"


# ---------------------------------------------------------------------------
# read_file_content
# ---------------------------------------------------------------------------
class TestReadFileContent:
    def test_utf8_file_reads_correctly(self, tmp_path: Path) -> None:
        """UTF-8 file returns content."""
        f = tmp_path / "hello.py"
        f.write_text("print('hello')", encoding="utf-8")
        assert read_file_content(str(f)) == "print('hello')"

    def test_cp1251_fallback(self, tmp_path: Path) -> None:
        """File that fails utf-8 but succeeds cp1251."""
        f = tmp_path / "cyrillic.txt"
        f.write_bytes("Привет".encode("cp1251"))
        result = read_file_content(str(f))
        assert result is not None
        assert "Привет" in result

    def test_all_encodings_fail(self, tmp_path: Path) -> None:
        """All encodings raise UnicodeDecodeError -> None and error message."""
        f = tmp_path / "broken.bin"
        f.write_bytes(b"\x80\x81")
        with (
            patch.object(Path, "read_text", side_effect=UnicodeDecodeError("fake", b"", 0, 1, "boom")),
            patch("exporter.processor.error") as mock_error,
        ):
            result = read_file_content(str(f))
            assert result is None
            mock_error.assert_called_once()
            assert "all encodings failed" in mock_error.call_args[0][0]

    def test_os_error_reported_and_returns_none(self, tmp_path: Path) -> None:
        """OSError during read -> error logged and None returned."""
        f = tmp_path / "unreadable.py"
        f.write_text("data")
        with (
            patch.object(Path, "read_text", side_effect=OSError("permission")),
            patch("exporter.processor.error") as mock_error,
        ):
            result = read_file_content(str(f))
            assert result is None
            mock_error.assert_called_once()
            assert "Error reading" in mock_error.call_args[0][0]


# ---------------------------------------------------------------------------
# _generate_structure_with_empty_dirs
# ---------------------------------------------------------------------------
class TestGenerateStructureWithEmptyDirs:
    def test_basic_tree(self, tmp_path: Path) -> None:
        """Simple directory with a file yields correct tree."""
        root = tmp_path / "project"
        root.mkdir()
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("code")
        processed = {"src/main.py"}
        config = {"blacklist_dirs": set()}
        result = _generate_structure_with_empty_dirs(str(root), processed, config)
        expected_lines = [
            "# Project Directory Structure:",
            "project/",
            "└── src/",
            "    └── main.py",
        ]
        assert result == "\n".join(expected_lines), f"Got:\n{result}"

    def test_dir_filter_out_hidden_and_blacklisted(self, tmp_path: Path) -> None:
        """Hidden and blacklisted dirs are skipped."""
        root = tmp_path / "app"
        root.mkdir()
        (root / "src").mkdir()
        (root / ".hidden").mkdir()
        (root / "node_modules").mkdir()
        (root / "src" / "file.py").write_text("x")
        processed = {"src/file.py"}
        config = {"blacklist_dirs": {"node_modules"}}
        result = _generate_structure_with_empty_dirs(str(root), processed, config)
        assert ".hidden" not in result
        assert "node_modules" not in result
        assert "src/" in result

    def test_gitignore_spec_applied_to_dirs(self, tmp_path: Path) -> None:
        """Directories matched by gitignore_spec are excluded."""
        root = tmp_path / "repo"
        root.mkdir()
        (root / "dist").mkdir()
        (root / "dist" / "bundle.js").write_text("//")
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("pass")
        processed = {"src/app.py"}
        config = {"blacklist_dirs": set()}
        # mock PathSpec to exclude "dist"
        mock_spec = MagicMock()

        # match_file returns True for dirs ending with /dist/
        mock_spec.match_file.return_value = False  # default

        def match_file(path: str) -> bool:
            # The real code calls with a trailing slash, e.g. "dist/"
            return path == "dist/"

        mock_spec.match_file.side_effect = match_file
        result = _generate_structure_with_empty_dirs(str(root), processed, config, gitignore_spec=mock_spec)
        assert "dist" not in result
        assert "src/" in result


# ---------------------------------------------------------------------------
# _generate_structure_with_depth
# ---------------------------------------------------------------------------
class TestGenerateStructureWithDepth:
    def test_simple_tree(self) -> None:
        processed = {"src/main.py", "src/utils.py"}
        extra_dirs = {"src"}
        result = _generate_structure_with_depth("/fake/proj", processed, extra_dirs)
        lines = result.splitlines()
        assert lines[0] == "# Project Directory Structure:"
        assert lines[1] == "proj/"
        assert any("src/" in line for line in lines), f"src/ not found in {lines}"
        assert any("main.py" in line for line in lines)
        assert any("utils.py" in line for line in lines)

    def test_extra_dirs_without_files(self) -> None:
        processed: set[str] = set()
        extra_dirs = {"lib"}
        result = _generate_structure_with_depth("/root", processed, extra_dirs)
        assert "lib/" in result

    def test_no_extra_dirs(self) -> None:
        processed = {"a.py"}
        result = _generate_structure_with_depth("/x", processed, set())
        assert "a.py" in result


# ---------------------------------------------------------------------------
# generate_project_structure
# ---------------------------------------------------------------------------
class TestGenerateProjectStructure:
    def test_show_empty_dirs_true_calls_sub_function(self) -> None:
        """When show_empty_dirs=True, delegates to _generate_structure_with_empty_dirs."""
        config = {"show_empty_dirs": True}
        with patch("exporter.processor._generate_structure_with_empty_dirs") as mock_empty:
            mock_empty.return_value = "tree"
            result = generate_project_structure("/dir", set(), config)
            assert result == "tree"
            mock_empty.assert_called_once_with("/dir", set(), config, None)

    def test_show_empty_dirs_false_builds_tree(self) -> None:
        """Without empty dirs, builds from processed_paths only."""
        config: dict[str, Any] = {"show_empty_dirs": False}
        result = generate_project_structure("/root", {"src/main.py"}, config)
        # basic check: structure header and filename
        assert "# Project Directory Structure:" in result
        assert "main.py" in result


# ---------------------------------------------------------------------------
# detect_language
# ---------------------------------------------------------------------------
class TestDetectLanguage:
    def test_known_extension(self) -> None:
        assert detect_language("script.py") == "python"

    def test_unknown_extension(self) -> None:
        assert detect_language("data.xyz") == ""

    def test_no_extension(self) -> None:
        assert detect_language("Dockerfile") == ""


# ---------------------------------------------------------------------------
# build_full_output
# ---------------------------------------------------------------------------
class TestBuildFullOutput:
    def test_structure_and_content_enabled(self) -> None:
        config = {"export_structure": True, "export_content": True}
        out = build_full_output("/p", {"a.py"}, ["a.py:\n```python\nprint(1)\n```\n\n"], config)
        assert "# Project Directory Structure:" in out
        assert "# BEGIN FILE CONTENTS" in out
        assert "print(1)" in out

    def test_only_structure(self) -> None:
        config = {"export_structure": True, "export_content": False}
        out = build_full_output("/p", {"a.py"}, [], config)
        assert "# Project Directory Structure:" in out
        assert "# BEGIN FILE CONTENTS" not in out

    def test_only_content(self) -> None:
        config = {"export_structure": False, "export_content": True}
        out = build_full_output("/p", {"a.py"}, ["code\n"], config)
        assert "Project Directory Structure" not in out
        assert "# BEGIN FILE CONTENTS" in out


# ---------------------------------------------------------------------------
# handle_clipboard_copy
# ---------------------------------------------------------------------------
class TestHandleClipboardCopy:
    def test_copy_disabled(self) -> None:
        assert handle_clipboard_copy("text", 10, copy_to_buffer=False, config={}) is False

    def test_exceeds_max_chars(self) -> None:
        with patch("exporter.processor.warning") as mock_warn:
            result = handle_clipboard_copy("x" * 100, 100, copy_to_buffer=True, config={"max_clipboard_chars": 50})
            assert result is False
            mock_warn.assert_called_once()
            assert "MAX_CLIPBOARD_CHARS" in mock_warn.call_args[0][0]

    def test_max_chars_zero_unlimited(self) -> None:
        with (
            patch("exporter.processor.copy_to_clipboard", return_value=True) as mock_copy,
            patch("exporter.processor.success") as mock_success,
        ):
            result = handle_clipboard_copy("long" * 1000, 4000, copy_to_buffer=True, config={"max_clipboard_chars": 0})
            assert result is True
            mock_success.assert_called_once()

    def test_copy_success(self) -> None:
        with (
            patch("exporter.processor.copy_to_clipboard", return_value=True) as mock_copy,
            patch("exporter.processor.success") as mock_success,
        ):
            result = handle_clipboard_copy("text", 4, copy_to_buffer=True, config={})
            assert result is True
            mock_success.assert_called_with("Content copied to clipboard")

    def test_copy_failure(self) -> None:
        with patch("exporter.processor.copy_to_clipboard", return_value=False):
            result = handle_clipboard_copy("x", 1, copy_to_buffer=True, config={})
            assert result is False


# ---------------------------------------------------------------------------
# _collect_files
# ---------------------------------------------------------------------------
class TestCollectFiles:
    def test_basic_collection(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Single directory with a .py file that passes all filters."""
        config = sample_config_dict.copy()
        # Remove blacklists that would exclude .py
        config["blacklist_extensions"] = set()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        config["max_depth"] = -1

        root = tmp_path / "proj"
        root.mkdir()
        py_file = root / "main.py"
        py_file.write_text("print('hello')")

        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, all_content, processed, extra, stats = _collect_files(str(root), config)
            assert processed == {"main.py"}, f"Expected {{'main.py'}}, got {processed}"
            assert len(all_content) == 1, f"Expected 1 content chunk, got {len(all_content)}"
            assert "main.py" in all_content[0], "'main.py' not found in first chunk"
            assert stats is not None, "stats should not be None"

    def test_skips_blacklisted_dir(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Directories matching blacklist_dirs are excluded."""
        config = sample_config_dict.copy()
        config["blacklist_dirs"] = {"venv"}
        root = tmp_path / "proj"
        root.mkdir()
        (root / "venv").mkdir()
        (root / "venv" / "lib.py").write_text("data")
        (root / "src").mkdir()
        (root / "src" / "main.py").write_text("code")
        # Only src/main.py should be collected
        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, _, processed, _, stats = _collect_files(str(root), config)
            assert "src/main.py" in processed, f"Expected 'src/main.py' in processed, got {processed}"
            assert all("venv" not in p for p in processed), "venv files should be excluded"
            assert stats is not None, "stats should not be None"

    def test_max_depth_limit(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """max_depth=1 includes files at depth 1, stops deeper recursion."""
        config = sample_config_dict.copy()
        config["blacklist_dirs"] = set()
        config["blacklist_extensions"] = set()
        config["max_depth"] = 1
        root = tmp_path / "root"
        root.mkdir()
        (root / "a.py").write_text("a")
        (root / "sub").mkdir()
        (root / "sub" / "b.py").write_text("b")
        (root / "sub" / "sub2").mkdir()
        (root / "sub" / "sub2" / "c.py").write_text("c")
        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, _, processed, extra, stats = _collect_files(str(root), config)
            # Root file is included
            assert "a.py" in processed, f"'a.py' missing from {processed}"
            # Files at depth 1 (max_depth) are included
            assert "sub/b.py" in processed, f"'sub/b.py' missing from {processed}"
            # Files deeper than max_depth are excluded
            assert "sub/sub2/c.py" not in processed, f"'sub/sub2/c.py' should not be in {processed}"
            # Directory at max_depth is marked as extra
            assert "sub" in extra, f"'sub' should be in extra dirs, got {extra}"
            assert stats is not None, "stats should not be None"

    def test_gitignore_filtering_applied(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Gitignore spec removes matching files/dirs."""
        config = sample_config_dict.copy()
        config["blacklist_dirs"] = set()
        config["blacklist_extensions"] = set()
        root = tmp_path / "repo"
        root.mkdir()
        (root / "dist").mkdir()
        (root / "dist" / "bundle.js").write_text("js")
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("py")
        # Mock PathSpec to exclude "dist/" directory and "dist/bundle.js" file
        mock_spec = MagicMock()

        def match_file(path: str) -> bool:
            return "dist" in path

        mock_spec.match_file.side_effect = match_file
        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, _, processed, _, stats = _collect_files(str(root), config, gitignore_spec=mock_spec)
            assert "src/app.py" in processed, f"Expected 'src/app.py', got {processed}"
            assert not any("dist" in p for p in processed), f"'dist' paths should be excluded: {processed}"
            assert stats is not None, "stats should not be None"

    def test_include_empty_files_flag(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """When include_empty_files=False, empty files are skipped."""
        config = sample_config_dict.copy()
        config["blacklist_dirs"] = set()
        config["blacklist_extensions"] = set()
        config["include_empty_files"] = False
        root = tmp_path / "proj"
        root.mkdir()
        (root / "empty.py").write_text("")
        (root / "nonempty.py").write_text("data")
        with patch("exporter.processor.is_code_file", return_value=True):
            _, _, processed, _, stats = _collect_files(str(root), config)
            assert "empty.py" not in processed, f"'empty.py' should be excluded, got {processed}"
            assert "nonempty.py" in processed, f"'nonempty.py' should be included, got {processed}"
            assert stats is not None, "stats should not be None"

    def test_export_content_false_skips_chunks(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """When export_content=False, all_content is empty but processed paths are recorded."""
        config = sample_config_dict.copy()
        config["blacklist_extensions"] = set()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        config["export_content"] = False
        config["include_empty_files"] = True  # empty files will be included (only in path)
        root = tmp_path / "proj"
        root.mkdir()
        (root / "file.py").write_text("data")
        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, all_content, processed, extra, stats = _collect_files(str(root), config)
            assert "file.py" in processed, f"Expected 'file.py' in processed, got {processed}"
            assert all_content == [], f"Expected empty content list, got {all_content}"
            assert stats is not None, "stats should not be None"

    def test_stats_skip_rules_count(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Files rejected by is_code_file should increment skipped_rules."""
        config = sample_config_dict.copy()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        # leave blacklist_extensions as is; .txt is blacklisted
        root = tmp_path / "proj"
        root.mkdir()
        (root / "readme.txt").write_text("text")
        (root / "script.py").write_text("print(1)")
        # is_code_file will return False for .txt, True for .py
        # we do NOT mock is_code_file, use real implementation from scanner
        files_by_dir, all_content, processed, extra, stats = _collect_files(str(root), config)
        assert "script.py" in processed, "script.py should be included"
        assert "readme.txt" not in processed, "readme.txt should be excluded"
        assert stats.skipped_rules == 1, f"Expected 1 skipped_rule, got {stats.skipped_rules}"

    def test_stats_skip_binary_and_size(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Binary files -> skipped_binary; oversized files -> skipped_size."""
        config = sample_config_dict.copy()
        config["blacklist_extensions"] = set()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        config["max_size"] = 100  # 100 bytes limit
        root = tmp_path / "proj"
        root.mkdir()
        (root / "good.py").write_text("ok")
        big_file = root / "big.py"
        big_file.write_text("x" * 200)  # 200 bytes (>100)
        binary_file = root / "bin.dat"
        binary_file.write_bytes(b"\x80\x81")

        with patch("exporter.processor.is_code_file", return_value=True):
            # patch read_file_content to return None for binary_file
            original_read = read_file_content

            def fake_read(path: str) -> str | None:
                if "bin.dat" in path:
                    return None
                return original_read(path)

            with patch("exporter.processor.read_file_content", side_effect=fake_read):
                files_by_dir, all_content, processed, extra, stats = _collect_files(str(root), config)

        assert "good.py" in processed
        assert "big.py" not in processed, "big.py should be skipped by size"
        assert "bin.dat" not in processed, "bin.dat should be skipped as binary"
        assert stats.skipped_binary == 1, f"Expected 1 skipped_binary, got {stats.skipped_binary}"
        assert stats.skipped_size == 1, f"Expected 1 skipped_size, got {stats.skipped_size}"

    def test_stats_extension_counts_and_largest_files(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Exported files should update extension_counts and largest_files."""
        config = sample_config_dict.copy()
        config["blacklist_extensions"] = set()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        root = tmp_path / "proj"
        root.mkdir()
        (root / "main.py").write_text("print('hi')")  # size ~11
        (root / "utils.py").write_text("def foo(): pass")  # size ~16
        (root / "script.js").write_text("console.log(1)")  # size ~16
        (root / "style.css").write_text("body{}")  # size ~5

        with patch("exporter.processor.is_code_file", return_value=True):
            _, _, processed, _, stats = _collect_files(str(root), config)

        assert len(processed) == 4, f"Expected 4 files, got {processed}"
        # Extension counts (py=2, js=1, css=1)
        assert stats.extension_counts.get("py") == 2, f"Expected 2 .py files, got {stats.extension_counts}"
        assert stats.extension_counts.get("js") == 1
        assert stats.extension_counts.get("css") == 1

        # largest_files contains all 4 files with sizes
        assert len(stats.largest_files) == 4
        sizes = {path: size for size, path in stats.largest_files}
        assert "main.py" in sizes
        assert sizes["main.py"] > 0

    def test_priority_sorting(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Files should be ordered by priority patterns, then depth, then name."""
        config = sample_config_dict.copy()
        config["blacklist_extensions"] = set()
        config["blacklist_dirs"] = set()
        config["blacklist_filenames"] = set()
        config["priority_patterns"] = ["*.py"]  # higher priority
        config["low_priority_patterns"] = ["*.txt"]  # lower priority
        root = tmp_path / "proj"
        root.mkdir()
        (root / "README.md").write_text("readme")
        (root / "sub").mkdir()
        (root / "sub" / "helper.py").write_text("helper")
        (root / "main.py").write_text("main")
        (root / "notes.txt").write_text("notes")

        with patch("exporter.processor.is_code_file", return_value=True):
            files_by_dir, all_content, processed, extra, stats = _collect_files(str(root), config)

        # Expected order: high priority *.py (sorted by depth, then name):
        #  main.py (depth 1) first, then sub/helper.py (depth 2)
        # Next neutral files: *.md (depth 1) -> README.md
        # Last low priority: *.txt -> notes.txt
        # The chunk string contains the path, we can extract paths
        paths_in_order = []
        for chunk in all_content:
            # chunk format: "rel_path:\n```...", get first line
            first_line = chunk.split("\n")[0]
            if ":" in first_line:
                paths_in_order.append(first_line.split(":")[0])

        assert paths_in_order == ["main.py", "sub/helper.py", "README.md", "notes.txt"], (
            f"Unexpected order: {paths_in_order}"
        )


# ---------------------------------------------------------------------------
# _build_output
# ---------------------------------------------------------------------------
class TestBuildOutput:
    def test_unlimited_depth_calls_full_output(self) -> None:
        config = {"max_depth": -1}
        with patch("exporter.processor.build_full_output", return_value="full") as mock_full:
            result = _build_output("/in", set(), [], set(), config)
            assert result == "full"
            mock_full.assert_called_once()

    def test_limited_depth_uses_structure_with_depth(self) -> None:
        config = {"max_depth": 0, "export_structure": True, "export_content": True}
        extra = {"sub"}
        with patch("exporter.processor._generate_structure_with_depth", return_value="tree\n") as mock_gen:
            result = _build_output("/in", {"a.py"}, ["content\n"], extra, config)
            assert "tree" in result
            assert "# BEGIN FILE CONTENTS" in result
            mock_gen.assert_called_once_with("/in", {"a.py"}, extra)


# ---------------------------------------------------------------------------
# export_project
# ---------------------------------------------------------------------------
class TestExportProject:
    def test_full_flow(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """End-to-end with mocks for file creation and clipboard."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = False
        config["create_file"] = True
        config["copy_to_buffer"] = True
        input_dir = str(tmp_path / "input")
        os.makedirs(input_dir, exist_ok=True)
        output_file = str(tmp_path / "output" / "out.txt")

        # Prepare mock for internal dependencies
        files_by_dir = {".": ["main.py"]}
        all_content = ["main.py:\n```python\nprint(1)\n```\n\n"]
        processed_paths = {"main.py"}
        extra_dirs: set[str] = set()
        full_output = "# output\ncontent"
        # stats can be any ExportStats-like object; a MagicMock works for testing
        mock_stats = MagicMock()
        with (
            patch(
                "exporter.processor._collect_files",
                return_value=(files_by_dir, all_content, processed_paths, extra_dirs, mock_stats),
            ) as mock_collect,
            patch("exporter.processor._build_output", return_value=full_output) as mock_build,
            patch("exporter.processor.handle_clipboard_copy") as mock_handle,
        ):
            result = export_project(input_dir, output_file, config, create_file=True, copy_to_buffer=True)
            # Check that _collect_files called
            mock_collect.assert_called_once()
            # _build_output called
            mock_build.assert_called_once()
            # handle_clipboard_copy called with correct args
            mock_handle.assert_called_once_with(full_output, len(full_output), copy_to_buffer=True, config=config)
            # file written
            out_path = Path(output_file)
            assert out_path.parent.exists(), f"Output directory {out_path.parent} should exist"
            assert out_path.read_text() == full_output, f"File content mismatch: {out_path.read_text()}"
            # return tuple now has 4 elements (files_by_dir, total_chars, full_output, stats)
            assert len(result) == 4, f"Expected 4-tuple, got {result}"
            returned_files, returned_chars, returned_output, returned_stats = result
            assert returned_files == files_by_dir, f"Files mismatch: {returned_files}"
            assert returned_chars == len(full_output), "Character count mismatch"
            assert returned_output == full_output, "Full output mismatch"
            assert returned_stats is mock_stats, "stats object should be the same mock"

    def test_oserror_during_file_write_logs_error(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """If write_output raises OSError, error is logged but does not raise."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = False
        input_dir = str(tmp_path / "in")
        os.makedirs(input_dir, exist_ok=True)
        output_file = str(tmp_path / "out.txt")

        files_by_dir = {".": ["main.py"]}
        all_content: list[str] = []
        processed_paths = {"main.py"}
        extra_dirs: set[str] = set()
        full_output = "content"
        mock_stats = MagicMock()
        with (
            patch(
                "exporter.processor._collect_files",
                return_value=(files_by_dir, all_content, processed_paths, extra_dirs, mock_stats),
            ),
            patch("exporter.processor._build_output", return_value=full_output),
            patch("pathlib.Path.mkdir"),
            patch.object(Path, "write_text", side_effect=OSError("disk full")),
            patch("exporter.processor.error") as mock_error,
            patch("exporter.processor.warning") as mock_warning,
            patch("exporter.processor.handle_clipboard_copy"),
        ):
            export_project(input_dir, output_file, config, create_file=True, copy_to_buffer=False)
            mock_error.assert_called_once()
            assert "disk full" in mock_error.call_args[0][0]
            mock_warning.assert_called_once()

    def test_gitignore_warning_when_not_found(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """USE_GITIGNORE=True but no .gitignore -> warning."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = True
        root = tmp_path / "proj"
        root.mkdir()
        with (
            patch("exporter.processor.warning") as mock_warn,
            patch("exporter.processor._collect_files", return_value=({}, [], set(), set(), MagicMock())),
            patch("exporter.processor._build_output", return_value=""),
            patch("exporter.processor.handle_clipboard_copy"),
        ):
            export_project(str(root), "out.txt", config, create_file=False, copy_to_buffer=False)
            mock_warn.assert_called_once()
            assert "USE_GITIGNORE is True" in mock_warn.call_args[0][0]

    def test_full_flow_with_real_gitignore(self, sample_config_dict: dict[str, Any], tmp_path: Path) -> None:
        """Integration test: project with .gitignore excludes matching files."""
        config = sample_config_dict.copy()
        config["use_gitignore"] = True
        config["export_structure"] = True
        config["export_content"] = True
        config["create_file"] = False
        config["copy_to_buffer"] = False
        config["blacklist_dirs"] = set()
        config["blacklist_extensions"] = set()
        config["blacklist_filenames"] = set()
        root = tmp_path / "repo"
        root.mkdir()
        (root / ".gitignore").write_text("*.log\ndist/\n")
        (root / "main.py").write_text("print(1)")
        (root / "debug.log").write_text("log data")
        (root / "dist").mkdir()
        (root / "dist" / "bundle.js").write_text("js")
        output_file = str(tmp_path / "out.txt")
        result = export_project(str(root), output_file, config, create_file=False, copy_to_buffer=False)
        files_by_dir, total_chars, full_output, stats = result
        # main.py should be present, .log and dist/ excluded
        assert "main.py" in str(files_by_dir), "main.py should be collected"
        assert not any("debug.log" in p for d in files_by_dir for p in files_by_dir[d])
        assert not any("dist" in p for d in files_by_dir for p in files_by_dir[d])
        # full_output should not contain .log content
        assert "log data" not in full_output
        # stats should be valid
        assert stats is not None

    def test_limited_depth_export_content_false(self) -> None:
        """max_depth=0, export_content=False -> structure only, no BEGIN FILE CONTENTS."""
        config: dict[str, Any] = {
            "max_depth": 0,
            "export_structure": True,
            "export_content": False,
        }
        extra = set()
        with patch("exporter.processor._generate_structure_with_depth", return_value="tree\n") as mock_gen:
            result = _build_output("/in", {"a.py"}, [], extra, config)
            assert "tree" in result
            assert "# BEGIN FILE CONTENTS" not in result
            mock_gen.assert_called_once_with("/in", {"a.py"}, extra)
