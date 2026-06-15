"""Shared fixtures and mocks for CodeExportForAI tests."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def sample_project_structure(tmp_path: Path) -> Path:
    """Create a temporary project directory with sample files.

    Structure:
        root/
        ├── src/
        │   ├── main.py
        │   ├── utils.py
        │   └── empty_file.txt   (empty)
        ├── tests/
        │   └── test_main.py
        ├── .gitignore
        ├── Dockerfile
        └── README.md
    """
    root = tmp_path / "sample_project"
    root.mkdir()
    (root / "src").mkdir()
    (root / "tests").mkdir()

    (root / "src" / "main.py").write_text("print('hello')")
    (root / "src" / "utils.py").write_text("def util(): pass")
    (root / "src" / "empty_file.txt").write_text("")
    (root / "tests" / "test_main.py").write_text("def test(): pass")
    (root / ".gitignore").write_text("*.log\n/dist/\n")
    (root / "Dockerfile").write_text("FROM python:3.10")
    (root / "README.md").write_text("# Sample Project")
    return root


@pytest.fixture
def sample_config_dict() -> dict[str, Any]:
    """Return a minimal valid configuration dictionary for testing."""
    return {
        "blacklist_extensions": {
            "txt",
            "md",
            "log",
            "pdf",
            "png",
            "jpg",
            "pyc",
            "ini",
            "cfg",
            "conf",
            "env",
        },
        "blacklist_dirs": {
            "__pycache__",
            ".git",
            ".vscode",
            "node_modules",
            "venv",
            "dist",
            "build",
        },
        "blacklist_filenames": {"setup.py", "requirements.txt"},
        "filename_filter_mode": "exact",
        "output_dir": "outputs",
        "default_output": "output.txt",
        "max_size": 5 * 1024 * 1024,  # 5 MB
        "create_file": True,
        "copy_to_buffer": False,
        "include_empty_files": True,
        "export_structure": True,
        "export_content": True,
        "show_empty_dirs": False,
        "max_clipboard_chars": 500000,
        "max_depth": -1,
        "use_gitignore": False,
        "allowed_extensionless_files": {"Dockerfile", "Makefile", "README", "LICENSE"},
    }


@pytest.fixture
def mock_clipboard() -> MagicMock:
    """Mock clipboard.copy_to_clipboard to return True."""
    with patch("exporter.processor.copy_to_clipboard") as mock_copy:
        mock_copy.return_value = True
        yield mock_copy


@pytest.fixture
def mock_console() -> dict[str, MagicMock]:
    """Mock all console output functions.

    Returns a dict with keys: info, warning, error, success, header, prompt.
    Prompt defaults to returning an empty string.
    """
    with (
        patch("exporter.console.info") as mock_info,
        patch("exporter.console.warning") as mock_warning,
        patch("exporter.console.error") as mock_error,
        patch("exporter.console.success") as mock_success,
        patch("exporter.console.header") as mock_header,
        patch("exporter.console.prompt") as mock_prompt,
    ):
        mock_prompt.return_value = ""
        yield {
            "info": mock_info,
            "warning": mock_warning,
            "error": mock_error,
            "success": mock_success,
            "header": mock_header,
            "prompt": mock_prompt,
        }


@pytest.fixture
def mock_tiktoken() -> MagicMock:
    """Mock tiktoken.get_encoding to return a fake encoder."""
    with patch("exporter.utils.tiktoken.get_encoding") as mock_get_enc:
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = [1, 2, 3]
        mock_get_enc.return_value = mock_encoder
        yield mock_get_enc


@pytest.fixture
def mock_tkinter() -> dict[str, MagicMock]:
    """Mock tkinter components for GUI folder selection tests."""
    with (
        patch("exporter.utils.tk.Tk") as mock_tk,
        patch("exporter.utils.filedialog.askdirectory") as mock_askdir,
    ):
        mock_askdir.return_value = ""
        yield {"tk": mock_tk, "askdirectory": mock_askdir}


@pytest.fixture
def mock_pathspec() -> MagicMock:
    """Mock pathspec.PathSpec to ignore all files by default."""
    with patch("exporter.processor.PathSpec") as mock_class:
        mock_spec = MagicMock()
        mock_spec.match_file.return_value = False
        mock_class.from_lines.return_value = mock_spec
        yield mock_class


@pytest.fixture
def mock_input() -> MagicMock:
    """Mock builtins.input to prevent test hangs."""
    with patch("builtins.input") as mock_in:
        mock_in.return_value = ""
        yield mock_in
