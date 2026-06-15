"""Unit tests for exporter/clipboard.py."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from exporter.clipboard import (
    _copy_linux,
    _copy_macos,
    _copy_windows,
    _copy_with_native,
    _copy_with_pyperclip,
    _get_command_path,
    copy_to_clipboard,
)


# ---------- helpers ----------
def _mock_which(path: str | None) -> MagicMock:
    """Return a pre-configured shutil.which mock that returns `path`."""
    mock = MagicMock(return_value=path)
    return mock


@pytest.fixture
def mock_subprocess_run() -> MagicMock:
    """Return a mock for subprocess.run that succeeds by default."""
    with patch("exporter.clipboard.subprocess.run") as m:
        m.return_value = MagicMock()  # success
        yield m


# =====================================================================
# _get_command_path
# =====================================================================
class TestGetCommandPath:
    @pytest.mark.parametrize(
        ("systemroot", "clip_exists"),
        [
            ("C:\\Windows", True),
            (None, True),  # falls back to C:\Windows
            ("C:\\Windows", False),  # no clip.exe
        ],
    )
    def test_windows_clip(self, monkeypatch: pytest.MonkeyPatch, systemroot: str | None, clip_exists: bool) -> None:
        """On win32, special handling for 'clip' command."""
        monkeypatch.setattr(sys, "platform", "win32")
        if systemroot is not None:
            monkeypatch.setenv("SYSTEMROOT", systemroot)
        else:
            monkeypatch.delenv("SYSTEMROOT", raising=False)

        with patch.object(Path, "exists", return_value=clip_exists):
            result = _get_command_path("clip")
            if clip_exists:
                expected_dir = systemroot or "C:\\Windows"
                expected = [str(Path(expected_dir) / "System32" / "clip.exe")]
                assert result == expected, f"Expected {expected}, got {result}"
            else:
                assert result is None, f"Expected None when clip.exe missing, got {result}"

    def test_other_command_found(self) -> None:
        """Non-clip command uses shutil.which, returns list with path."""
        with patch("shutil.which", return_value="/usr/bin/pbcopy"):
            result = _get_command_path("pbcopy")
            assert result == ["/usr/bin/pbcopy"], f"Expected list, got {result}"

    def test_other_command_not_found(self) -> None:
        """shutil.which returns None -> None."""
        with patch("shutil.which", return_value=None):
            result = _get_command_path("xclip")
            assert result is None, "Expected None for missing command"


# =====================================================================
# _copy_with_pyperclip
# =====================================================================
class TestCopyWithPyperclip:
    def test_pyperclip_not_available(self) -> None:
        """HAS_PYPERCLIP is False -> returns None."""
        with patch("exporter.clipboard.HAS_PYPERCLIP", False):
            result = _copy_with_pyperclip("test")
            assert result is None, "Should return None when pyperclip absent"

    def test_copy_succeeds(self) -> None:
        """pyperclip.copy doesn't raise -> True."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", True),
            patch("exporter.clipboard.pyperclip.copy") as mock_copy,
        ):
            result = _copy_with_pyperclip("hello")
            assert result is True
            mock_copy.assert_called_once_with("hello")

    def test_copy_raises_exception(self) -> None:
        """pyperclip.copy raises an exception -> False, error logged."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", True),
            patch("exporter.clipboard.pyperclip.copy", side_effect=RuntimeError("clip fail")),
            patch("exporter.clipboard.error") as mock_error,
        ):
            result = _copy_with_pyperclip("boom")
            assert result is False
            mock_error.assert_called_once()
            assert "clip fail" in mock_error.call_args[0][0]


# =====================================================================
# _copy_windows
# =====================================================================
class TestCopyWindows:
    def test_clip_found_success(self, mock_subprocess_run: MagicMock) -> None:
        """_get_command_path returns path, subprocess.run succeeds -> True."""
        with patch("exporter.clipboard._get_command_path", return_value=["clip.exe"]):
            result = _copy_windows("text")
            assert result is True
            mock_subprocess_run.assert_called_once_with(["clip.exe"], input="text", text=True, check=True)

    def test_clip_found_subprocess_error(self, mock_subprocess_run: MagicMock) -> None:
        """subprocess.run raises SubprocessError -> False, error logged."""
        mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "clip")
        with (
            patch("exporter.clipboard._get_command_path", return_value=["clip.exe"]),
            patch("exporter.clipboard.error") as mock_error,
        ):
            result = _copy_windows("text")
            assert result is False
            mock_error.assert_called_once()

    def test_clip_not_found(self) -> None:
        """_get_command_path returns None -> False."""
        with patch("exporter.clipboard._get_command_path", return_value=None):
            result = _copy_windows("text")
            assert result is False


# =====================================================================
# _copy_macos
# =====================================================================
class TestCopyMacos:
    def test_pbcopy_found_success(self, mock_subprocess_run: MagicMock) -> None:
        with patch("exporter.clipboard._get_command_path", return_value=["/usr/bin/pbcopy"]):
            result = _copy_macos("text")
            assert result is True
            mock_subprocess_run.assert_called_once_with(["/usr/bin/pbcopy"], input="text", text=True, check=True)

    def test_pbcopy_found_subprocess_error(self, mock_subprocess_run: MagicMock) -> None:
        mock_subprocess_run.side_effect = subprocess.SubprocessError("fail")
        with (
            patch("exporter.clipboard._get_command_path", return_value=["/usr/bin/pbcopy"]),
            patch("exporter.clipboard.error") as mock_error,
        ):
            result = _copy_macos("text")
            assert result is False
            mock_error.assert_called_once()

    def test_pbcopy_not_found(self) -> None:
        with patch("exporter.clipboard._get_command_path", return_value=None):
            result = _copy_macos("text")
            assert result is False


# =====================================================================
# _copy_linux
# =====================================================================
class TestCopyLinux:
    def test_xclip_success(self, mock_subprocess_run: MagicMock) -> None:
        with patch("exporter.clipboard._get_command_path", side_effect=[["/usr/bin/xclip"]]):
            result = _copy_linux("text")
            assert result is True
            mock_subprocess_run.assert_called_once_with(
                ["/usr/bin/xclip", "-selection", "clipboard"],
                input="text",
                text=True,
                check=True,
            )

    def test_xclip_fail_then_xsel_success(self, mock_subprocess_run: MagicMock) -> None:
        """Xclip fails (subprocess error), xsel succeeds."""
        mock_subprocess_run.side_effect = [
            subprocess.SubprocessError("xclip fail"),  # first call for xclip fails
            None,  # second call (xsel) succeeds
        ]
        with patch(
            "exporter.clipboard._get_command_path",
            side_effect=[["/usr/bin/xclip"], ["/usr/bin/xsel"]],
        ):
            result = _copy_linux("text")
            assert result is True
            assert mock_subprocess_run.call_count == 2

    def test_xclip_not_found_xsel_success(self, mock_subprocess_run: MagicMock) -> None:
        """Xclip not found, xsel found and works."""
        with patch(
            "exporter.clipboard._get_command_path",
            side_effect=[None, ["/usr/bin/xsel"]],
        ):
            result = _copy_linux("text")
            assert result is True
            mock_subprocess_run.assert_called_once_with(
                ["/usr/bin/xsel", "--clipboard", "--input"],
                input="text",
                text=True,
                check=True,
            )

    def test_both_not_found(self) -> None:
        with patch("exporter.clipboard._get_command_path", return_value=None):
            result = _copy_linux("text")
            assert result is False

    def test_both_fail(self, mock_subprocess_run: MagicMock) -> None:
        """Xclip and xsel both raise subprocess errors."""
        mock_subprocess_run.side_effect = subprocess.SubprocessError("fail")
        with patch(
            "exporter.clipboard._get_command_path",
            side_effect=[["/usr/bin/xclip"], ["/usr/bin/xsel"]],
        ):
            result = _copy_linux("text")
            assert result is False


# =====================================================================
# _copy_with_native
# =====================================================================
class TestCopyWithNative:
    @pytest.mark.parametrize(
        "platform_name,expected_func",
        [
            ("win32", "_copy_windows"),
            ("darwin", "_copy_macos"),
            ("linux", "_copy_linux"),
        ],
    )
    def test_dispatches_to_correct_function(
        self, platform_name: str, expected_func: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "platform", platform_name)
        with patch(f"exporter.clipboard.{expected_func}", return_value=True) as mock_func:
            result = _copy_with_native("text")
            assert result is True
            mock_func.assert_called_once_with("text")

    def test_other_platform_calls_linux(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sys, "platform", "freebsd")
        with patch("exporter.clipboard._copy_linux", return_value=False) as mock_linux:
            assert _copy_with_native("text") is False
            mock_linux.assert_called_once_with("text")

    def test_oserror_caught(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unexpected OSError during dispatch is caught and returns False."""
        monkeypatch.setattr(sys, "platform", "win32")
        with (
            patch("exporter.clipboard._copy_windows", side_effect=OSError("boom")),
            patch("exporter.clipboard.error") as mock_error,
        ):
            result = _copy_with_native("text")
            assert result is False
            mock_error.assert_called_once()


# =====================================================================
# copy_to_clipboard (public API)
# =====================================================================
class TestCopyToClipboard:
    def test_pyperclip_succeeds_no_native(self) -> None:
        """Pyperclip returns True → return True, native not called."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", True),
            patch("exporter.clipboard.pyperclip.copy") as mock_copy,
            patch("exporter.clipboard._copy_with_native") as mock_native,
        ):
            assert copy_to_clipboard("test") is True
            mock_copy.assert_called_once()
            mock_native.assert_not_called()

    def test_pyperclip_fails_fallback_native_succeeds(self) -> None:
        """Pyperclip returns False → fallback to native, which returns True."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", True),
            patch("exporter.clipboard.pyperclip.copy", side_effect=RuntimeError("fail")),
            patch("exporter.clipboard._copy_with_native", return_value=True) as mock_native,
            patch("exporter.clipboard.error") as mock_error,
        ):
            assert copy_to_clipboard("test") is True
            mock_native.assert_called_once_with("test")
            mock_error.assert_called_once()  # pyperclip error logged

    def test_pyperclip_not_available_native_succeeds(self) -> None:
        """Pyperclip not installed → native used."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", False),
            patch("exporter.clipboard._copy_with_native", return_value=True) as mock_native,
        ):
            assert copy_to_clipboard("test") is True
            mock_native.assert_called_once_with("test")

    def test_both_fail(self) -> None:
        """Pyperclip fails (or not avail) + native fails → False."""
        with (
            patch("exporter.clipboard.HAS_PYPERCLIP", False),
            patch("exporter.clipboard._copy_with_native", return_value=False),
        ):
            assert copy_to_clipboard("test") is False

    def test_pyperclip_true_no_fallback_triggered(self) -> None:
        """Pyperclip returns True directly, ignoring HAS_PYPERCLIP False edge redundant but okay."""
        # Actually if HAS_PYPERCLIP False, pyperclip result is None, not True.
        # So that case is covered already.
