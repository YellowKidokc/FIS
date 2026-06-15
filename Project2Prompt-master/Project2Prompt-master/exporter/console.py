"""Colored console output utilities using Rich."""

from rich.console import Console
from rich.markup import escape as escape_markup
from rich.theme import Theme

# --------------------------------------------------------------------------- #
#  Centralised Console instance (exported so other modules can print  trees)  #
# --------------------------------------------------------------------------- #

# Style theme – all output functions map messages to these named styles.
_theme = Theme({
    "info": "",
    "warning": "yellow",
    "error": "red",
    "success": "green",
    "header": "bold cyan",
    "prompt": "bright_blue",
})

console = Console(theme=_theme)

# --------------------------------------------------------------------------- #
#  Public API                                                                 #
# --------------------------------------------------------------------------- #


def info(msg: str) -> None:
    """Print informational message (no extra styling)."""
    console.print(msg, style="info")


def warning(msg: str) -> None:
    """Print warning message in yellow."""
    console.print(msg, style="warning")


def error(msg: str) -> None:
    """Print error message in red."""
    console.print(msg, style="error")


def success(msg: str) -> None:
    """Print success message in green."""
    console.print(msg, style="success")


def header(msg: str) -> None:
    """Print header message in bold cyan."""
    console.print(msg, style="header")


def prompt(msg: str) -> str:
    """Print a prompt in light blue and return user input.

    Note:
        The prompt text is escaped to prevent accidental Rich
        markup interpretation (e.g. brackets in user-facing strings).

    """
    safe_msg = escape_markup(msg)
    return console.input(f"[prompt]{safe_msg}[/]")
