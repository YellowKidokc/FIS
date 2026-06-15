"""Unit tests for main.py module."""

import argparse
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Mark all tests in this module to use the main.py module
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ---------------------------------------------------------------------------
# find_config_files
# ---------------------------------------------------------------------------
class TestFindConfigFiles:
    def test_returns_empty_list_when_configs_dir_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Configs directory does not exist -> returns empty list."""
        monkeypatch.setattr(Path, "is_dir", lambda self: (self.name == "xyz" and self.name == "configs") or False)
        # More straightforward: patch specific Path("configs").is_dir()
        with patch("main.Path") as mock_path:
            mock_path.return_value.is_dir.return_value = False
            from main import find_config_files

            result = find_config_files()
            assert result == [], "Expected empty list when configs/ is missing"

    def test_returns_sorted_py_files_excluding_init_and_hidden(self, tmp_path: Path) -> None:
        """Only .py files, not __init__.py or hidden, sorted alphabetically."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        (configs_dir / "b.py").touch()
        (configs_dir / "a.py").touch()
        (configs_dir / "__init__.py").touch()
        (configs_dir / ".hidden.py").touch()
        (configs_dir / "readme.md").touch()  # ignored

        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.return_value = configs_dir
            from main import find_config_files

            result = find_config_files()
            expected = [configs_dir / "a.py", configs_dir / "b.py"]
            assert result == expected, f"Expected {expected}, got {result}"

    def test_handles_oserror_and_returns_empty(self) -> None:
        """When rglob raises OSError, return [] and warn."""
        with (
            patch("main.Path") as mock_path,
            patch("main.warning") as mock_warning,
        ):
            mock_path.return_value.is_dir.return_value = True
            mock_path.return_value.rglob.side_effect = OSError("Permission denied")
            from main import find_config_files

            result = find_config_files()
            assert result == [], "Expected empty list on OSError"
            mock_warning.assert_called_once()
            assert "Cannot read 'configs/'" in mock_warning.call_args[0][0]


# ---------------------------------------------------------------------------
# select_config_file
# ---------------------------------------------------------------------------
class TestSelectConfigFile:
    def test_explicit_absolute_path_exists(self, tmp_path: Path) -> None:
        """When --config is an absolute path that exists, return it."""
        config = tmp_path / "my_config.py"
        config.touch()
        from main import select_config_file

        result = select_config_file(str(config))
        assert result == config, f"Expected {config}, got {result}"

    def test_explicit_absolute_path_not_found(self) -> None:
        """Absolute path given but missing -> error, return None."""
        abs_path = "/nonexistent/config.py"
        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(abs_path)
            assert result is None, "Expected None for missing absolute path"
            mock_error.assert_called_once()
            assert f"Configuration file not found: {abs_path}" in mock_error.call_args[0][0]

    def test_explicit_relative_exists_in_configs(self, tmp_path: Path) -> None:
        """Relative path that exists inside configs/ -> return it."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        config_file = configs_dir / "dev.py"
        config_file.touch()

        with patch("main.Path", wraps=Path) as mock_path:
            # Ensure Path("configs") returns tmp_path/configs
            mock_path.side_effect = lambda p, *args: Path(p) if p != "configs" else configs_dir
            from main import select_config_file

            result = select_config_file("dev.py")
            assert result == config_file, f"Expected {config_file}, got {result}"

    def test_explicit_relative_fallback_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Relative path not in configs but exists relative to CWD."""
        cwd_config = tmp_path / "local.py"
        cwd_config.touch()
        monkeypatch.chdir(tmp_path)

        # Ensure configs/ directory does not exist so the fallback is taken
        assert not Path("configs").exists(), "configs/ should not be present"

        from main import select_config_file

        result = select_config_file("local.py")
        assert result.resolve() == cwd_config.resolve(), f"Expected {cwd_config}, got {result}"

    def test_explicit_relative_not_found_anywhere(self) -> None:
        """Relative path not found -> error, return None."""
        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file("missing.py")
            assert result is None, "Expected None for missing relative config"
            mock_error.assert_called_once()
            assert "Configuration file not found: missing.py" in mock_error.call_args[0][0]

    def test_no_explicit_config_single_config_auto_select(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Only one config -> automatically selected and info printed."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        config_file = configs_dir / "only.py"
        config_file.touch()
        monkeypatch.chdir(tmp_path)

        with patch("main.info") as mock_info:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == config_file.resolve(), f"Expected {config_file}, got {result}"
            mock_info.assert_called_once()
            assert "only" in mock_info.call_args[0][0]

    def test_multiple_configs_prompt_valid_choice(
        self, mock_input: MagicMock, mock_console: dict[str, MagicMock], tmp_path: Path
    ) -> None:
        """Multiple configs: user picks a valid number."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        files = [configs_dir / "a.py", configs_dir / "b.py", configs_dir / "c.py"]
        for f in files:
            f.touch()

        mock_input.side_effect = ["2"]  # Choose b.py

        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.side_effect = lambda p: configs_dir if p == "configs" else Path(p)
            from main import select_config_file

            result = select_config_file(None)
            assert result == files[1], f"Expected {files[1]}, got {result}"

    def test_multiple_configs_invalid_then_valid_choice(
        self, mock_input: MagicMock, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """User enters invalid choice, then valid."""
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        files = [configs_dir / "x.py", configs_dir / "y.py"]
        for f in files:
            f.touch()
        monkeypatch.chdir(tmp_path)

        mock_input.side_effect = ["x", "-1", "0", "1"]

        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == files[0].resolve(), f"Expected {files[0]}, got {result}"
            assert mock_error.call_count == 3

    def test_no_configs_fallback_to_root_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configs/ dir, root config.py exists -> use it."""
        root_config = tmp_path / "config.py"
        root_config.touch()
        monkeypatch.chdir(tmp_path)

        with patch("main.warning") as mock_warning:
            from main import select_config_file

            result = select_config_file(None)
            assert result.resolve() == root_config.resolve(), f"Expected {root_config}, got {result}"
            mock_warning.assert_called_once()

    def test_no_configs_no_root_config_error(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No configs anywhere -> error, return None."""
        monkeypatch.chdir(tmp_path)  # tmp_path has no config.py

        with patch("main.error") as mock_error:
            from main import select_config_file

            result = select_config_file(None)
            assert result is None, "Expected None when no config found"
            mock_error.assert_called_once()


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------
class TestLoadConfig:
    @pytest.fixture
    def valid_config_content(self) -> str:
        """Content of a valid configuration file."""
        return """
BLACKLIST_EXTENSIONS = {"txt", "md"}
BLACKLIST_DIRS = {"__pycache__"}
BLACKLIST_FILENAMES = {"setup.py"}
FILENAME_FILTER_MODE = "exact"
OUTPUT_DIR = "outputs"
OUTPUT_FILENAME = "export.txt"
MAX_FILE_SIZE_MB = 5
CREATE_FILE = True
COPY_TO_CLIPBOARD = False
INCLUDE_EMPTY_FILES = True
EXPORT_STRUCTURE = True
EXPORT_CONTENT = True
SHOW_EMPTY_DIRS = False
MAX_CLIPBOARD_CHARS = 5000
MAX_DEPTH = -1
USE_GITIGNORE = False
ALLOWED_EXTENSIONLESS_FILES = {"Dockerfile"}
"""

    def test_loads_valid_config_and_transforms_keys(self, tmp_path: Path, valid_config_content: str) -> None:
        """Valid config -> returns dict with transformed keys."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)

        from main import load_config

        result = load_config(config_file)
        assert isinstance(result, dict), "Result should be a dict"
        assert result["output_dir"] == "outputs", "output_dir mismatch"
        assert result["default_output"] == "export.txt", "default_output mismatch"
        assert result["max_size"] == 5 * 1024 * 1024, "max_size should be 5 MB"
        assert result["create_file"] is True
        assert result["copy_to_buffer"] is False
        assert result["blacklist_extensions"] == {"txt", "md"}

    def test_missing_required_attribute_causes_system_exit(self, tmp_path: Path, mock_input: MagicMock) -> None:
        """Config file missing a required attr -> SystemExit."""
        config_file = tmp_path / "bad_config.py"
        config_file.write_text("BLACKLIST_EXTENSIONS = set()\n")

        with patch("main.error") as mock_error:
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
            mock_error.assert_called()
            mock_input.assert_called()

    def test_wrong_type_causes_system_exit(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """Attribute with wrong type -> SystemExit."""
        # Change MAX_DEPTH to a string
        bad_content = valid_config_content.replace("MAX_DEPTH = -1", 'MAX_DEPTH = "unlimited"')
        config_file = tmp_path / "config.py"
        config_file.write_text(bad_content)

        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(config_file)
        mock_input.assert_called()

    def test_max_depth_below_minus_one_exits(self, tmp_path: Path, valid_config_content: str) -> None:
        """MAX_DEPTH < -1 -> SystemExit (no input prompt)."""
        bad_content = valid_config_content.replace("MAX_DEPTH = -1", "MAX_DEPTH = -5")
        config_file = tmp_path / "config.py"
        config_file.write_text(bad_content)

        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(config_file)

    def test_file_not_found_causes_system_exit(self, mock_input: MagicMock) -> None:
        """Non-existent config path -> SystemExit."""
        with patch("main.error") as mock_error:
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(Path("ghost.py"))
            mock_error.assert_called()
            mock_input.assert_called()

    def test_import_failure_spec_is_none(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """spec_from_file_location returns None -> SystemExit."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)
        with patch("importlib.util.spec_from_file_location", return_value=None):
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
        mock_input.assert_called()

    def test_import_failure_exec_module_raises(
        self, tmp_path: Path, valid_config_content: str, mock_input: MagicMock
    ) -> None:
        """exec_module raises exception -> SystemExit."""
        config_file = tmp_path / "config.py"
        config_file.write_text(valid_config_content)
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            mock_spec.return_value.loader = MagicMock()
            mock_spec.return_value.loader.exec_module.side_effect = ImportError("boom")
            from main import load_config

            with pytest.raises(SystemExit, match="1"):
                load_config(config_file)
        mock_input.assert_called()

    def test_defaults_for_optional_attrs(self, tmp_path: Path, mock_input: MagicMock) -> None:
        """USE_GITIGNORE and ALLOWED_EXTENSIONLESS_FILES are optional."""
        # Content without those two
        content = """
BLACKLIST_EXTENSIONS = set()
BLACKLIST_DIRS = set()
BLACKLIST_FILENAMES = set()
FILENAME_FILTER_MODE = "exact"
OUTPUT_DIR = "out"
OUTPUT_FILENAME = "out.txt"
MAX_FILE_SIZE_MB = 1
CREATE_FILE = False
COPY_TO_CLIPBOARD = False
INCLUDE_EMPTY_FILES = False
EXPORT_STRUCTURE = False
EXPORT_CONTENT = False
SHOW_EMPTY_DIRS = False
MAX_CLIPBOARD_CHARS = 0
MAX_DEPTH = 0
"""
        config_file = tmp_path / "config.py"
        config_file.write_text(content)
        from main import load_config

        result = load_config(config_file)
        assert result.get("use_gitignore") is False, "default use_gitignore should be False"
        assert result.get("allowed_extensionless_files") == set(), (
            "default allowed_extensionless_files should be empty set"
        )


# ---------------------------------------------------------------------------
# check_export_options
# ---------------------------------------------------------------------------
class TestCheckExportOptions:
    def test_both_outputs_disabled_enables_file(self, sample_config_dict: dict[str, Any]) -> None:
        """Both create_file and copy_to_buffer False -> info, set create_file True."""
        cfg = sample_config_dict.copy()
        cfg["create_file"] = False
        cfg["copy_to_buffer"] = False

        with patch("main.info") as mock_info:
            from main import check_export_options

            result = check_export_options(cfg)
            assert result["create_file"] is True, "Expected create_file to be enabled"
            mock_info.assert_called()
            assert "File output enabled" in mock_info.call_args[0][0]

    def test_both_export_flags_disabled_user_confirms(self, sample_config_dict: dict[str, Any]) -> None:
        """Both export flags False; user confirms -> export_content True."""
        cfg = sample_config_dict.copy()
        cfg["export_structure"] = False
        cfg["export_content"] = False

        with (
            patch("main.prompt", return_value="y"),
            patch("main.warning") as mock_warning,
        ):
            from main import check_export_options

            result = check_export_options(cfg)
            assert result["export_content"] is True, "Expected export_content to be enabled"
            mock_warning.assert_called()

    def test_both_export_flags_disabled_user_rejects(self, sample_config_dict: dict[str, Any]) -> None:
        """User rejects enabling content -> returns empty dict."""
        cfg = sample_config_dict.copy()
        cfg["export_structure"] = False
        cfg["export_content"] = False

        with (
            patch("main.prompt", return_value="n"),
            patch("main.warning") as mock_warning,
        ):
            from main import check_export_options

            result = check_export_options(cfg)
            assert result == {}, "Expected empty dict when user rejects"
            mock_warning.assert_called()

    def test_no_changes_when_ok(self, sample_config_dict: dict[str, Any]) -> None:
        """Nothing to change -> returns same config."""
        cfg = sample_config_dict.copy()
        from main import check_export_options

        result = check_export_options(cfg)
        assert result == cfg, "Config should be unchanged"


# ---------------------------------------------------------------------------
# parse_arguments
# ---------------------------------------------------------------------------
class TestParseArguments:
    def test_defaults(self) -> None:
        """No arguments -> output and directory and config are None."""
        with patch.object(sys, "argv", ["main.py"]):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output is None
            assert args.directory is None
            assert args.config is None

    def test_all_args_short(self) -> None:
        """Short flags provided."""
        argv = ["main.py", "-o", "out.txt", "-d", "/tmp/project", "-c", "dev"]
        with patch.object(sys, "argv", argv):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output == "out.txt", f"Expected 'out.txt', got {args.output}"
            assert args.directory == "/tmp/project"
            assert args.config == "dev"

    def test_all_args_long(self) -> None:
        """Long flags provided."""
        argv = ["main.py", "--output", "export.py", "--directory", "src", "--config", "prod"]
        with patch.object(sys, "argv", argv):
            from main import parse_arguments

            args = parse_arguments()
            assert args.output == "export.py"
            assert args.directory == "src"
            assert args.config == "prod"


# ---------------------------------------------------------------------------
# get_input_directory
# ---------------------------------------------------------------------------
class TestGetInputDirectory:
    def test_directory_arg_exists(self, tmp_path: Path) -> None:
        """-d argument points to existing directory -> return it."""
        d = tmp_path / "project"
        d.mkdir()
        args = argparse.Namespace(directory=str(d))
        from main import get_input_directory

        result = get_input_directory(args, "")
        assert result == str(d), f"Expected {d}, got {result}"

    def test_directory_arg_not_a_directory(self, tmp_path: Path) -> None:
        """-d argument is not a directory -> error, return None."""
        f = tmp_path / "file.txt"
        f.touch()
        args = argparse.Namespace(directory=str(f))

        with patch("main.error") as mock_error:
            from main import get_input_directory

            result = get_input_directory(args, "")
            assert result is None, "Expected None for non-directory"
            mock_error.assert_called()

    def test_no_directory_arg_select_success(self, tmp_path: Path) -> None:
        """No -d, select_directory returns a path."""
        args = argparse.Namespace(directory=None)
        selected = tmp_path / "chosen"
        selected.mkdir()

        with (
            patch("main.select_directory", return_value=str(selected)),
            patch("main.info") as mock_info,
        ):
            from main import get_input_directory

            result = get_input_directory(args, "")
            assert result == str(selected), f"Expected {selected}, got {result}"
            mock_info.assert_called()

    def test_no_directory_arg_select_cancelled(self) -> None:
        """No -d, select_directory returns None."""
        args = argparse.Namespace(directory=None)

        with (
            patch("main.select_directory", return_value=None),
            patch("main.error") as mock_error,
        ):
            from main import get_input_directory

            result = get_input_directory(args, "")
            assert result is None, "Expected None when selection cancelled"
            mock_error.assert_called()


# ---------------------------------------------------------------------------
# get_output_filename
# ---------------------------------------------------------------------------
class TestGetOutputFilename:
    def test_absolute_output_arg(self, sample_config_dict: dict[str, Any]) -> None:
        """Absolute -o returns as string."""
        expected = str(Path("/absolute/path/out.txt"))
        args = argparse.Namespace(output="/absolute/path/out.txt")

        from main import get_output_filename

        result = get_output_filename(args, sample_config_dict, create_file=True)
        assert result == expected, f"Unexpected {result}"

    def test_relative_output_arg_prepends_output_dir(self, sample_config_dict: dict[str, Any]) -> None:
        """Relative -o is placed inside output_dir."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "outputs/prod"
        args = argparse.Namespace(output="result.txt")
        from main import get_output_filename

        result = get_output_filename(args, cfg, create_file=False)
        expected = str(Path("outputs/prod/result.txt"))
        assert result == expected, f"Expected {expected}, got {result}"

    def test_no_output_arg_uses_default_and_unique(
        self, sample_config_dict: dict[str, Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No -o, create_file=True -> calls get_next_filename."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "out"
        cfg["default_output"] = "export.txt"
        args = argparse.Namespace(output=None)

        with patch("main.get_next_filename") as mock_next:
            mock_next.return_value = "out/export_5.txt"
            from main import get_output_filename

            result = get_output_filename(args, cfg, create_file=True)
            mock_next.assert_called_once_with(str(Path("out/export.txt")))
            assert result == "out/export_5.txt"

    def test_no_output_arg_create_file_false(self, sample_config_dict: dict[str, Any]) -> None:
        """No -o, create_file=False -> returns candidate without uniqueness."""
        cfg = sample_config_dict.copy()
        cfg["output_dir"] = "out"
        cfg["default_output"] = "export.txt"
        args = argparse.Namespace(output=None)

        from main import get_output_filename

        result = get_output_filename(args, cfg, create_file=False)
        expected = str(Path("out/export.txt"))
        assert result == expected, f"Expected {expected}, got {result}"


# ---------------------------------------------------------------------------
# perform_export
# ---------------------------------------------------------------------------
class TestPerformExport:
    def test_calls_export_and_statistics(
        self,
        sample_config_dict: dict[str, Any],
        mock_console: dict[str, MagicMock],
        mock_clipboard: MagicMock,
    ) -> None:
        """perform_export should call export_project and print_statistics."""
        from main import perform_export

        with (
            patch("main.export_project") as mock_export,
            patch("main.print_statistics") as mock_stats,
            patch("main.time.time", side_effect=[100.0, 101.5]),
        ):
            mock_stats_obj = MagicMock()  # dummy ExportStats
            mock_export.return_value = ({"src": ["main.py"]}, 42, "full output", mock_stats_obj)
            perform_export(
                input_dir="/project",
                output_file="/out.txt",
                config=sample_config_dict,
                create_file=True,
                copy_to_buffer=False,
            )
            mock_export.assert_called_once_with(
                "/project",
                "/out.txt",
                sample_config_dict,
                create_file=True,
                copy_to_buffer=False,
            )
            mock_stats.assert_called_once()
            # Check output_info passed
            output_info_arg = mock_stats.call_args[0][3]
            assert output_info_arg.output_file == "/out.txt"
            assert output_info_arg.create_file is True
            assert output_info_arg.copy_to_buffer is False


# ---------------------------------------------------------------------------
# load_app_config
# ---------------------------------------------------------------------------
class TestLoadAppConfig:
    def test_config_exists_returns_true(self, tmp_path: Path) -> None:
        config_file = tmp_path / "app_config.py"
        config_file.write_text("CHECK_FOR_UPDATES = True\n")
        with patch("main.Path", return_value=config_file):
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": True}

    def test_config_exists_returns_false(self, tmp_path: Path) -> None:
        config_file = tmp_path / "app_config.py"
        config_file.write_text("CHECK_FOR_UPDATES = False\n")
        with patch("main.Path", return_value=config_file):
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": False}

    def test_config_missing_defaults_to_true(self) -> None:
        with patch("main.Path.is_file", return_value=False):
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": True}

    def test_spec_none_logs_warning_and_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "app_config.py"
        config_file.touch()
        with (
            patch("main.Path", return_value=config_file),
            patch("importlib.util.spec_from_file_location", return_value=None),
            patch("main.warning") as mock_warn,
        ):
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": True}
        mock_warn.assert_called_once()

    def test_exec_module_raises_logs_warning_and_defaults(self, tmp_path: Path) -> None:
        config_file = tmp_path / "app_config.py"
        config_file.touch()
        with (
            patch("main.Path", return_value=config_file),
            patch("main.warning") as mock_warn,
            patch("importlib.util.spec_from_file_location") as mock_spec,
        ):
            mock_loader = MagicMock()
            mock_loader.exec_module.side_effect = SyntaxError("bad")
            mock_spec.return_value.loader = mock_loader
            from main import load_app_config

            result = load_app_config()
        assert result == {"check_for_updates": True}
        mock_warn.assert_called_once()


# ---------------------------------------------------------------------------
# _get_config_description
# ---------------------------------------------------------------------------
class TestGetConfigDescription:
    def test_simple_description(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text('CONFIG_DESCRIPTION = "A short description"\n')
        from main import _get_config_description

        assert _get_config_description(cfg) == "A short description"

    def test_multiline_uses_first_non_empty_line(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text('CONFIG_DESCRIPTION = """\n\n  First line  \n  Second\n"""\n')
        from main import _get_config_description

        assert _get_config_description(cfg) == "First line"

    def test_long_description_truncated(self, tmp_path: Path) -> None:
        long_desc = "A" * 100
        cfg = tmp_path / "cfg.py"
        cfg.write_text(f'CONFIG_DESCRIPTION = "{long_desc}"\n')
        from main import _get_config_description

        result = _get_config_description(cfg)
        assert len(result) == 80
        assert result.endswith("...")

    def test_no_variable_returns_none(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text("OTHER = 42\n")
        from main import _get_config_description

        assert _get_config_description(cfg) is None

    def test_non_string_value_returns_none(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text("CONFIG_DESCRIPTION = 123\n")
        from main import _get_config_description

        assert _get_config_description(cfg) is None

    def test_syntax_error_returns_none(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text("CONFIG_DESCRIPTION = incomplete\n")
        from main import _get_config_description

        assert _get_config_description(cfg) is None

    def test_read_error_returns_none(self, tmp_path: Path) -> None:
        cfg = tmp_path / "cfg.py"
        cfg.write_text('CONFIG_DESCRIPTION = "ok"')
        with patch.object(Path, "read_text", side_effect=OSError("denied")):
            from main import _get_config_description

            assert _get_config_description(cfg) is None


# ---------------------------------------------------------------------------
# _resolve_config_path
# ---------------------------------------------------------------------------
class TestResolveConfigPath:
    def test_absolute_path_exists(self, tmp_path: Path) -> None:
        p = tmp_path / "abs.py"
        p.touch()
        from main import _resolve_config_path

        assert _resolve_config_path(str(p)) == p

    def test_absolute_path_missing(self) -> None:
        from main import _resolve_config_path

        assert _resolve_config_path("/no/such/path.py") is None

    def test_inside_configs_dir(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        configs = tmp_path / "configs"
        configs.mkdir()
        cfg = configs / "dev.py"
        cfg.touch()
        monkeypatch.chdir(tmp_path)
        from main import _resolve_config_path

        result = _resolve_config_path("dev.py")
        assert result is not None
        assert result.resolve() == cfg.resolve()

    def test_relative_to_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cfg = tmp_path / "local.py"
        cfg.touch()
        monkeypatch.chdir(tmp_path)
        from main import _resolve_config_path

        result = _resolve_config_path("local.py")
        assert result is not None
        assert result.resolve() == cfg.resolve()

    def test_not_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        from main import _resolve_config_path

        assert _resolve_config_path("ghost.py") is None


# ---------------------------------------------------------------------------
# Additional get_input_directory scenarios
# ---------------------------------------------------------------------------
class TestGetInputDirectoryAdditional:
    def test_config_input_dir_valid_used(self, tmp_path: Path) -> None:
        preset = tmp_path / "preset"
        preset.mkdir()
        args = argparse.Namespace(directory=None)
        from main import get_input_directory

        assert get_input_directory(args, str(preset)) == str(preset)

    def test_config_input_dir_is_file_warns_and_fallsback(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.touch()
        args = argparse.Namespace(directory=None)
        with (
            patch("main.warning") as mock_warn,
            patch("main.select_directory", return_value=str(tmp_path)),
        ):
            from main import get_input_directory

            result = get_input_directory(args, str(f))
        mock_warn.assert_called_once()
        assert result == str(tmp_path)

    def test_config_input_dir_nonexistent_warns_and_fallsback(self, tmp_path: Path) -> None:
        args = argparse.Namespace(directory=None)
        with (
            patch("main.warning") as mock_warn,
            patch("main.select_directory", return_value=str(tmp_path)),
        ):
            from main import get_input_directory

            result = get_input_directory(args, "/ghost")
        mock_warn.assert_called_once()
        assert result == str(tmp_path)

    def test_cli_overrides_config_preset(self, tmp_path: Path) -> None:
        cli_dir = tmp_path / "cli"
        cli_dir.mkdir()
        preset_dir = tmp_path / "preset"
        preset_dir.mkdir()
        args = argparse.Namespace(directory=str(cli_dir))
        from main import get_input_directory

        assert get_input_directory(args, str(preset_dir)) == str(cli_dir)


# ---------------------------------------------------------------------------
# Additional load_config scenarios
# ---------------------------------------------------------------------------
class TestLoadConfigAdditional:
    @pytest.fixture
    def base_valid_content(self) -> str:
        return (
            "BLACKLIST_EXTENSIONS = set()\n"
            "BLACKLIST_DIRS = set()\n"
            "BLACKLIST_FILENAMES = set()\n"
            "FILENAME_FILTER_MODE = 'exact'\n"
            "OUTPUT_DIR = 'out'\n"
            "OUTPUT_FILENAME = 'out.txt'\n"
            "MAX_FILE_SIZE_MB = 5\n"
            "CREATE_FILE = True\n"
            "COPY_TO_CLIPBOARD = False\n"
            "INCLUDE_EMPTY_FILES = True\n"
            "EXPORT_STRUCTURE = True\n"
            "EXPORT_CONTENT = True\n"
            "SHOW_EMPTY_DIRS = False\n"
            "MAX_CLIPBOARD_CHARS = 5000\n"
            "MAX_DEPTH = -1\n"
            "USE_GITIGNORE = False\n"
            "ALLOWED_EXTENSIONLESS_FILES = set()\n"
        )

    def test_input_dir_present_in_config(self, tmp_path: Path, base_valid_content: str) -> None:
        content = base_valid_content + 'INPUT_DIR = "/some/path"\n'
        cfg = tmp_path / "config.py"
        cfg.write_text(content)
        from main import load_config

        result = load_config(cfg)
        assert result["input_dir"] == "/some/path"

    def test_input_dir_wrong_type_exits(self, tmp_path: Path, base_valid_content: str) -> None:
        content = base_valid_content + "INPUT_DIR = 123\n"
        cfg = tmp_path / "config.py"
        cfg.write_text(content)
        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(cfg)

    def test_priority_patterns_loaded(self, tmp_path: Path, base_valid_content: str) -> None:
        content = base_valid_content + 'PRIORITY_PATTERNS = ["*.py"]\nLOW_PRIORITY_PATTERNS = ["*.txt"]\n'
        cfg = tmp_path / "config.py"
        cfg.write_text(content)
        from main import load_config

        result = load_config(cfg)
        assert result["priority_patterns"] == ["*.py"]
        assert result["low_priority_patterns"] == ["*.txt"]

    def test_priority_patterns_wrong_type_exits(self, tmp_path: Path, base_valid_content: str) -> None:
        content = base_valid_content + "PRIORITY_PATTERNS = '*.py'\n"
        cfg = tmp_path / "config.py"
        cfg.write_text(content)
        from main import load_config

        with pytest.raises(SystemExit, match="1"):
            load_config(cfg)

    def test_max_file_size_zero_logs_info(self, tmp_path: Path, base_valid_content: str) -> None:
        content = base_valid_content.replace("MAX_FILE_SIZE_MB = 5", "MAX_FILE_SIZE_MB = 0")
        cfg = tmp_path / "config.py"
        cfg.write_text(content)
        with patch("main.info") as mock_info:
            from main import load_config

            load_config(cfg)
        mock_info.assert_any_call(
            "MAX_FILE_SIZE_MB = 0 — file size limit disabled. All files will be included regardless of size."
        )


# ---------------------------------------------------------------------------
# _display_config_tree
# ---------------------------------------------------------------------------
class TestDisplayConfigTree:
    def test_empty_list_produces_no_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        from main import _display_config_tree

        _display_config_tree([])
        assert capsys.readouterr().out == ""

    def test_single_file_with_description(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        cfg = configs_dir / "test.py"
        cfg.write_text('CONFIG_DESCRIPTION = "My config"\n')
        with patch("main.Path", wraps=Path) as mock_path:
            mock_path.side_effect = lambda p: configs_dir if p == "configs" else Path(p)
            from main import _display_config_tree

            _display_config_tree([cfg])
        captured = capsys.readouterr().out
        assert "1. test" in captured
        assert "My config" in captured


# ---------------------------------------------------------------------------
# Additional perform_export checks
# ---------------------------------------------------------------------------
class TestPerformExportAdditional:
    def test_logs_directory_and_output_paths(
        self,
        sample_config_dict: dict[str, Any],
    ) -> None:
        from main import perform_export

        with (
            patch("main.info") as mock_info,
            patch("main.export_project", return_value=({}, 0, "", MagicMock())),
            patch("main.print_statistics"),
            patch("main.time.time", side_effect=[1.0, 2.0]),
        ):
            perform_export(
                input_dir="/my/project",
                output_file="/out.txt",
                config=sample_config_dict,
                create_file=False,
                copy_to_buffer=False,
            )
        info_calls = [c[0][0] for c in mock_info.call_args_list]
        assert any("Directory: /my/project" in msg for msg in info_calls)
        assert any("Output file: /out.txt" in msg for msg in info_calls)


# ---------------------------------------------------------------------------
# Minimal main() integration test
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def test_single_run_exports_and_quits(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        mock_input: MagicMock,
    ) -> None:
        configs_dir = tmp_path / "configs"
        configs_dir.mkdir()
        cfg = configs_dir / "test.py"
        cfg.write_text(
            "BLACKLIST_EXTENSIONS = set()\n"
            "BLACKLIST_DIRS = set()\n"
            "BLACKLIST_FILENAMES = set()\n"
            "FILENAME_FILTER_MODE = 'exact'\n"
            "OUTPUT_DIR = 'out'\n"
            "OUTPUT_FILENAME = 'out.txt'\n"
            "MAX_FILE_SIZE_MB = 5\n"
            "CREATE_FILE = True\n"
            "COPY_TO_CLIPBOARD = False\n"
            "INCLUDE_EMPTY_FILES = True\n"
            "EXPORT_STRUCTURE = True\n"
            "EXPORT_CONTENT = True\n"
            "SHOW_EMPTY_DIRS = False\n"
            "MAX_CLIPBOARD_CHARS = 5000\n"
            "MAX_DEPTH = -1\n"
            "USE_GITIGNORE = False\n"
            "ALLOWED_EXTENSIONLESS_FILES = set()\n"
        )
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "main.py").write_text("print(1)")
        monkeypatch.chdir(tmp_path)
        mock_input.side_effect = ["n"]

        with (
            patch("sys.argv", ["main.py"]),
            patch("main.check_for_updates"),
            patch("main.select_directory", return_value=str(project_dir)),
            patch(
                "main.export_project",
                return_value=({".": ["main.py"]}, 100, "fake output", MagicMock()),
            ) as mock_export,
            patch("main.print_statistics"),
            patch("main.check_export_options", side_effect=lambda cfg: cfg),
        ):
            from main import main

            main()
            mock_export.assert_called_once()
