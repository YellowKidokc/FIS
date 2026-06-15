"""Unit tests for exporter/utils.py."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from exporter.utils import (
    OutputInfo,
    _build_file_tree,
    get_next_filename,
    print_statistics,
    select_directory,
)


# ---------------------------------------------------------------------------
# select_directory
# ---------------------------------------------------------------------------
class TestSelectDirectory:
    def test_gui_returns_selected_folder(self, tmp_path: Path) -> None:
        """Tkinter dialog returns a path -> returned as string."""
        selected = tmp_path / "selected_folder"
        selected.mkdir()

        with (
            patch("tkinter.Tk") as mock_tk,
            patch("tkinter.filedialog.askdirectory", return_value=str(selected)),
        ):
            result = select_directory()
            assert result == str(selected), f"Expected {selected}, got {result}"
            mock_tk.return_value.withdraw.assert_called()
            mock_tk.return_value.destroy.assert_called()

    def test_gui_returns_empty_string_cancels(self) -> None:
        """Tkinter returns empty string -> falls back to manual input."""
        manual_input = "/valid_dir"
        expected = str(Path(manual_input).expanduser().resolve())
        with (
            patch("tkinter.Tk"),
            patch("tkinter.filedialog.askdirectory", return_value=""),
            patch("exporter.utils.input", side_effect=[manual_input]),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning"),
            patch("exporter.utils.error") as mock_error,
        ):
            result = select_directory()
            assert result == expected, f"Expected {expected}, got {result}"
            mock_error.assert_not_called()

    def test_import_error_falls_back_to_manual(self) -> None:
        """Tkinter import fails -> warning, then manual input."""
        with (
            patch("exporter.utils.input", return_value="/manual_dir"),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning") as mock_warn,
        ):
            # Simulate ImportError by removing tkinter from sys.modules temporarily?
            # We'll directly patch the 'import tkinter' inside select_directory.
            # Use a mock that raises ImportError when the import is attempted.
            original_import = __import__

            def fake_import(name, *args, **kwargs):
                if name == "tkinter":
                    raise ImportError("tkinter not available")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                result = select_directory()
                # select_directory returns an absolute, resolved path.
                # Compare Path objects to be cross‑platform.
                expected = Path("/manual_dir").resolve()
                assert Path(result) == expected, f"Expected {expected}, got {result}"
                mock_warn.assert_called_once()

    def test_tcl_error_falls_back_to_manual(self) -> None:
        """TclError during tkinter usage -> warning, manual fallback."""
        pytest.importorskip("tkinter")
        import tkinter

        manual_input = "/tcl_fallback"
        expected_path = str(Path(manual_input).expanduser().resolve())
        with (
            patch("tkinter.Tk", side_effect=tkinter.TclError("TclError")),
            patch("exporter.utils.input", return_value=manual_input),
            patch("exporter.utils.Path.is_dir", return_value=True),
            patch("exporter.utils.warning") as mock_warn,
        ):
            result = select_directory()
            assert result == expected_path, f"Expected {expected_path}, got {result}"
            mock_warn.assert_called_once()

    def test_manual_cancelled_returns_none(self) -> None:
        """Manual input with empty line returns None."""
        with (
            patch("exporter.utils.input", return_value=""),
            patch("exporter.utils.Path.is_dir", return_value=False),  # not needed
            patch("exporter.utils.info") as mock_info,
        ):
            # Trigger fallback by making tkinter import fail
            with patch("builtins.__import__", side_effect=ImportError):
                result = select_directory()
                assert result is None, "Empty manual input should cancel"
                mock_info.assert_called()  # prompt message

    def test_manual_invalid_then_valid_path(self) -> None:
        """Manual input first invalid, then valid -> returns valid path."""
        valid_dir = Path("/real_dir")
        with (
            patch("exporter.utils.input", side_effect=["bad_dir", str(valid_dir)]),
            patch("exporter.utils.Path.is_dir", side_effect=[False, True]),
            patch("exporter.utils.error") as mock_error,
            patch("exporter.utils.info") as mock_info,
        ):
            # Make tkinter import fail to go straight to manual
            with patch("builtins.__import__", side_effect=ImportError):
                result = select_directory()
                # select_directory resolves the path → compare resolved Path objects
                assert Path(result) == valid_dir.resolve(), f"Expected {valid_dir.resolve()}, got {result}"
                mock_error.assert_called_once()  # first invalid attempt
                # info called twice: initial prompt + prompt after error
                assert mock_info.call_count == 2


# ---------------------------------------------------------------------------
# get_next_filename
# ---------------------------------------------------------------------------
class TestGetNextFilename:
    def test_no_existing_files_returns_counter_1(self, tmp_path: Path) -> None:
        """No files -> returns base with _1 suffix."""
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_1.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_existing_counter_increments_max(self, tmp_path: Path) -> None:
        """Existing output_3.txt -> returns output_4.txt."""
        (tmp_path / "output_3.txt").write_text("")
        (tmp_path / "other.txt").write_text("")  # not relevant
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_4.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_ignores_non_matching_pattern(self, tmp_path: Path) -> None:
        """Only files matching stem_<digit>.suffix are considered."""
        (tmp_path / "output_abc.txt").write_text("")
        (tmp_path / "output_1.txt").write_text("")
        base = str(tmp_path / "output.txt")
        expected = str(tmp_path / "output_2.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_handles_no_extension(self, tmp_path: Path) -> None:
        """No extension in base -> suffix empty, returns stem_1."""
        base = str(tmp_path / "Dockerfile")
        expected = str(tmp_path / "Dockerfile_1")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_multiple_digits_in_counter(self, tmp_path: Path) -> None:
        """Counter can be multi-digit, max 12 -> 13."""
        (tmp_path / "export_12.md").write_text("")
        base = str(tmp_path / "export.md")
        expected = str(tmp_path / "export_13.md")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"

    def test_non_existent_parent(self, tmp_path: Path) -> None:
        """Parent directory does not exist; still returns counter 1."""
        base = str(tmp_path / "nonexistent" / "output.txt")
        expected = str(tmp_path / "nonexistent" / "output_1.txt")
        result = get_next_filename(base)
        assert result == expected, f"Expected {expected}, got {result}"


# ---------------------------------------------------------------------------
# _build_file_tree
# ---------------------------------------------------------------------------
class TestBuildFileTree:
    def test_basic_tree_structure(self) -> None:
        files = {
            "src": ["main.py", "utils.py"],
            "src/sub": ["helper.py"],
            ".": ["README.md"],
        }
        root = "myproject"
        tree = _build_file_tree(files, root)
        lines = tree.splitlines()
        assert lines[0] == "myproject/"
        # Directories first, then files in root: so src/ before README.md
        assert lines[1] == "├── src/"
        assert lines[2] == "│   ├── sub/"
        assert lines[3] == "│   │   └── helper.py"
        assert lines[4] == "│   ├── main.py"
        assert lines[5] == "│   └── utils.py"
        assert lines[6] == "└── README.md"

    def test_empty_dict_returns_only_root(self) -> None:
        tree = _build_file_tree({}, "empty_root")
        expected = "empty_root/"
        assert tree == expected, f"Expected {expected!r}, got {tree!r}"

    def test_all_files_in_root(self) -> None:
        files = {".": ["a.py", "b.py"]}
        tree = _build_file_tree(files, "root")
        # Should have root line, then files sorted
        expected_lines = [
            "root/",
            "├── a.py",
            "└── b.py",
        ]
        assert tree == "\n".join(expected_lines), f"Tree mismatch: {tree}"


# ---------------------------------------------------------------------------
# print_statistics
# ---------------------------------------------------------------------------
class TestPrintStatistics:
    def test_outputs_all_sections(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Full statistics printed with mocked tiktoken and console."""
        files_by_dir = {"src": ["main.py"], "tests": ["test_main.py"]}
        total_chars = 5000
        elapsed_time = 1.2
        output_info = OutputInfo(output_file="out.txt", create_file=True, copy_to_buffer=False)
        input_dir = "/project"
        full_output = "some content"

        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success") as mock_success,
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = [0] * 100  # 100 tokens
            mock_enc.return_value = mock_encoder

            print_statistics(
                files_by_dir,
                total_chars,
                elapsed_time,
                output_info,
                input_dir,
                full_output,
            )

            # Check that success was called at the end
            mock_success.assert_called_once()
            # The success message should mention "saved to out.txt"
            assert "saved to out.txt" in mock_success.call_args[0][0]

        # Also check that token count was printed (with ANSI color codes)
        captured = capsys.readouterr()
        assert "Tokens:" in captured.out
        # The token count appears as ~\x1b[32m100\x1b[0m; check that "100" is present
        assert "100" in captured.out

    def test_elapsed_time_color_coding(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Elapsed time color green (<1s)."""
        output_info = OutputInfo("out.txt", False, False)
        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success"),
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = []
            mock_enc.return_value = mock_encoder
            print_statistics(
                {".": ["a.py"]},
                100,
                0.5,
                output_info,
                "/root",
                "hello",
            )
        captured = capsys.readouterr()
        # Should contain green color code \033[32m before time
        assert "\033[32m" in captured.out

    def test_file_size_mb_when_large(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Characters >= 1 MB displayed in MB."""
        output_info = OutputInfo("big.txt", False, False)
        total_chars = 2 * 1024 * 1024  # 2 MB
        with (
            patch("exporter.utils.tiktoken.get_encoding") as mock_enc,
            patch("exporter.utils.success"),
        ):
            mock_encoder = MagicMock()
            mock_encoder.encode.return_value = []
            mock_enc.return_value = mock_encoder
            print_statistics(
                {".": ["large.bin"]},
                total_chars,
                0.1,
                output_info,
                "/root",
                "data",
            )
        captured = capsys.readouterr()
        assert "2.00 MB" in captured.out
