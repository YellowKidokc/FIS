"""Cross-platform clipboard operations module."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from exporter.console import error

# Attempt to import pyperclip at top level
try:
    import pyperclip

    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False


def _get_command_path(cmd: str) -> list[str] | None:
    """
    Return the full command path as a single-element list for subprocess.

    Returns None if the command is not found.
    Special handling for Windows clip command.
    """
    if sys.platform == "win32" and cmd == "clip":
        system_root = os.environ.get("SYSTEMROOT", "C:\\Windows")
        clip_path = Path(system_root) / "System32" / "clip.exe"
        if clip_path.exists():
            return [str(clip_path)]
        return None

    full_path = shutil.which(cmd)
    return [full_path] if full_path else None


def _copy_with_pyperclip(text: str) -> bool | None:
    """Try to copy using pyperclip. Return True on success, False on failure, None if not available."""
    if not HAS_PYPERCLIP:
        return None
    try:
        pyperclip.copy(text)
    except Exception as e:  # noqa: BLE001
        # Pyperclip can raise various exceptions; we just log and fall back.
        error(f"Pyperclip error: {e}")
        return False
    else:
        return True


def _copy_windows(text: str) -> bool:
    """Copy using Windows clip command."""
    cmd_path = _get_command_path("clip")
    if cmd_path is None:
        return False
    try:
        # cmd_path is already a list; do not wrap it again
        subprocess.run(cmd_path, input=text, text=True, check=True)  # noqa: S603
    except (OSError, subprocess.SubprocessError) as e:
        error(f"Windows clipboard error: {e}")
        return False
    else:
        return True


def _copy_macos(text: str) -> bool:
    """Copy using macOS pbcopy command."""
    cmd_path = _get_command_path("pbcopy")
    if cmd_path is None:
        return False
    try:
        # cmd_path is already a list; do not wrap it again
        subprocess.run(cmd_path, input=text, text=True, check=True)  # noqa: S603
    except (OSError, subprocess.SubprocessError) as e:
        error(f"macOS clipboard error: {e}")
        return False
    else:
        return True


def _copy_linux(text: str) -> bool:
    """Copy using Linux xclip or xsel commands."""
    for cmd in ("xclip", "xsel"):
        cmd_path = _get_command_path(cmd)
        if cmd_path is None:
            continue

        # cmd_path is a list; build the full command by concatenation
        if cmd == "xclip":
            cmd_list = cmd_path + ["-selection", "clipboard"]
        else:  # xsel
            cmd_list = cmd_path + ["--clipboard", "--input"]

        try:
            subprocess.run(cmd_list, input=text, text=True, check=True)  # noqa: S603
        except subprocess.SubprocessError:
            continue
        else:
            return True

    return False


def _copy_with_native(text: str) -> bool:
    """Try to copy using native system tools based on platform."""
    platform = sys.platform
    try:
        if platform == "win32":
            return _copy_windows(text)
        if platform == "darwin":
            return _copy_macos(text)
        # Linux and others
        return _copy_linux(text)
    except (OSError, subprocess.SubprocessError) as e:
        error(f"Native clipboard error: {e}")
        return False


def copy_to_clipboard(text: str) -> bool:
    """
    Copy text to clipboard in a cross-platform way.

    Order of attempts:
    1. pyperclip (if installed)
    2. Native tools: clip (Windows), pbcopy (macOS), xclip/xsel (Linux)

    Args:
        text: The text to copy to the clipboard.

    Returns:
        True on success, False otherwise.

    """
    # 1. Try pyperclip
    pyperclip_result = _copy_with_pyperclip(text)
    if pyperclip_result is True:
        return True
    # If pyperclip is not available or failed (False), fall through to native tools.

    # 2. Fall back to native tools
    return _copy_with_native(text)
