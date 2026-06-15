"""Unit tests for exporter/scanner.py."""

from typing import Any
from unittest.mock import patch

import pytest

from exporter.scanner import is_code_file


# ---------------------------------------------------------------------------
# helper to quickly build a config dict for scanner tests
# ---------------------------------------------------------------------------
def _make_config(**overrides: Any) -> dict[str, Any]:
    """Return a minimal valid scanner config with optional overrides."""
    base = {
        "blacklist_extensions": {"txt", "log"},
        "blacklist_dirs": {"__pycache__", "node_modules"},
        "blacklist_filenames": {"setup.py", "requirements.txt"},
        "filename_filter_mode": "exact",
        "allowed_extensionless_files": {"Dockerfile", "Makefile"},
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestIsCodeFile:
    # ----- Hidden files -----
    def test_hidden_file_rejected(self) -> None:
        """Files starting with a dot are skipped."""
        cfg = _make_config()
        assert is_code_file(".hidden.py", cfg) is False, ".hidden.py should be rejected"

    # ----- Filename blacklist exact -----
    @pytest.mark.parametrize(
        "filename",
        ["setup.py", "requirements.txt"],
    )
    def test_exact_blacklist_rejected(self, filename: str) -> None:
        """Exact blacklist match -> False."""
        cfg = _make_config(filename_filter_mode="exact")
        assert is_code_file(filename, cfg) is False, f"{filename} should be blacklisted exactly"

    def test_exact_blacklist_not_matching_other(self) -> None:
        """Not an exact match -> True."""
        cfg = _make_config(filename_filter_mode="exact")
        assert is_code_file("app.py", cfg) is True, "app.py should not be blacklisted"

    # ----- Filename blacklist contains -----
    def test_contains_blacklist_rejected(self) -> None:
        """Fragment appears anywhere in filename -> False."""
        cfg = _make_config(
            filename_filter_mode="contains",
            blacklist_filenames={"min.", "bundle."},
        )
        assert is_code_file("app.min.js", cfg) is False, "app.min.js should match 'min.'"
        assert is_code_file("vendor.bundle.js", cfg) is False, "vendor.bundle.js should match 'bundle.'"

    def test_contains_blacklist_not_matching(self) -> None:
        """No fragment overlaps -> True."""
        cfg = _make_config(
            filename_filter_mode="contains",
            blacklist_filenames={"min.", "bundle."},
        )
        assert is_code_file("app.js", cfg) is True, "app.js should not match blacklist"

    # ----- Invalid filter mode edge-case: blacklist check is skipped -----
    def test_unknown_filter_mode_ignores_blacklist(self) -> None:
        """When mode is not 'exact' or 'contains', filename blacklist is bypassed."""
        cfg = _make_config(
            filename_filter_mode="invalid",
            blacklist_filenames={"setup.py"},
        )
        assert is_code_file("setup.py", cfg) is True, "setup.py should pass when mode is unknown"

    # ----- Parent directory blacklist -----
    def test_parent_dir_blacklisted(self) -> None:
        """File directly inside a blacklisted directory -> False; only immediate parent is checked."""
        cfg = _make_config()
        # path.parent.name is 'node_modules'
        assert is_code_file("node_modules/foo.py", cfg) is False, "node_modules should be blacklisted"
        # nested deeper: parent is 'lib', not blacklisted → True
        assert is_code_file("node_modules/lib/bar.py", cfg) is True, (
            "Only immediate parent directory 'lib' is checked, not blacklisted"
        )
        # Let's adjust: based on code, it only checks immediate parent directory name, not ancestors. So file in node_modules/lib/bar.py will have parent name "lib", not blacklisted -> returns True (unless blacklisted by extension). This test would fail if we expect False. So we'll remove that sub-case and only test direct child.
        # Correction: The code only checks path.parent.name, not whole path. So we'll test direct child.

    def test_nested_dir_not_blacklisted(self) -> None:
        """Only immediate parent directory is checked."""
        cfg = _make_config()
        # lib is not blacklisted
        assert is_code_file("node_modules/lib/bar.py", cfg) is True, "lib is not blacklisted, should pass"

    # ----- Extension blacklist -----
    @pytest.mark.parametrize("ext", ["txt", "log"])
    def test_blacklisted_extension_rejected(self, ext: str) -> None:
        """Blacklisted extension -> False."""
        cfg = _make_config()
        filename = f"readme.{ext}"
        assert is_code_file(filename, cfg) is False, f"{ext} should be blacklisted"

    def test_allowed_extension_accepted(self) -> None:
        """Not in blacklist, no size limit -> True."""
        cfg = _make_config()
        assert is_code_file("main.py", cfg) is True

    # ----- Extensionless files -----
    def test_extensionless_file_not_whitelisted(self) -> None:
        """File without extension and not in allowed_extensionless -> False."""
        cfg = _make_config()
        assert is_code_file("README", cfg) is False, "README is not whitelisted by default"
        # now add it
        cfg["allowed_extensionless_files"] = {"README"}
        assert is_code_file("README", cfg) is True, "README now allowed"

    def test_extensionless_file_whitelisted(self) -> None:
        """File on the extensionless whitelist -> True."""
        cfg = _make_config()
        assert is_code_file("Dockerfile", cfg) is True, "Dockerfile is in allowed list"

    def test_extensionless_blacklist_not_applied_by_extension(self) -> None:
        """Extensionless file is not blocked by blacklisted extensions (since ext is empty)."""
        cfg = _make_config()
        # Dockerfile has no extension, so blacklist_extensions doesn't apply. Should be True.
        assert is_code_file("Dockerfile", cfg) is True

    # ----- Size limits -----
    def test_size_within_limit(self) -> None:
        """File size less than max_size -> True."""
        cfg = _make_config(max_size=1024)  # 1 KB
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 512
            assert is_code_file("small.py", cfg) is True, "512 B < 1024 B should be allowed"

    def test_size_exceeds_limit(self) -> None:
        """File size > max_size -> False."""
        cfg = _make_config(max_size=100)
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 200
            assert is_code_file("big.py", cfg) is False, "200 B > 100 B should be rejected"

    def test_max_size_zero_or_none_disables_limit(self) -> None:
        """max_size = 0 or None means no limit."""
        cfg_zero = _make_config(max_size=0)
        cfg_none = _make_config(max_size=None)
        # No stat patching needed because if max_size is falsy, stat is not called.
        assert is_code_file("any.py", cfg_zero) is True
        assert is_code_file("any.py", cfg_none) is True

    # ----- OSError during stat -----
    def test_stat_oserror_logs_warning_and_skips(self) -> None:
        """When stat raises OSError, warning is printed and file is skipped."""
        cfg = _make_config(max_size=1024)
        with (
            patch("pathlib.Path.stat", side_effect=OSError("permission denied")),
            patch("exporter.console.warning") as mock_warn,
        ):
            assert is_code_file("inaccessible.py", cfg) is False, "OSError should cause skip"
            mock_warn.assert_called_once()
            assert "permission denied" in mock_warn.call_args[0][0]

    # ----- Case insensitivity -----
    def test_extension_case_insensitivity(self) -> None:
        """Uppercase extensions are still matched against extension blacklist."""
        cfg = _make_config()
        assert is_code_file("README.TXT", cfg) is False, "TXT should match txt"
        # filename blacklist is case‑sensitive; 'setup.PY' ≠ 'setup.py' → not rejected
        assert is_code_file("setup.PY", cfg) is True, (
            "setup.PY does not match setup.py exactly, so it passes filename filter"
        )
        # test blacklist extension
        assert is_code_file("note.LOG", cfg) is False, "LOG should match log"

    # ----- Files with multiple dots -----
    def test_multiple_dots_extension(self) -> None:
        """Only the part after the last dot is used as extension."""
        cfg = _make_config(blacklist_extensions={"gz"})
        assert is_code_file("archive.tar.gz", cfg) is False, "gz should be blacklisted"
        # Not blacklisted
        cfg2 = _make_config(blacklist_extensions={"tar"})
        assert is_code_file("archive.tar.gz", cfg2) is True, "tar is not the last extension"
