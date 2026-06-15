"""Utility to check for newer versions of Project2Prompt from GitHub releases."""

import json
import urllib.error
import urllib.request

from exporter.console import warning


def check_for_updates(current_version: str) -> None:
    """Check if a newer version is available on GitHub and warn the user.

    Queries the latest release from the repo's GitHub API and compares
    the tag version against *current_version*. If a newer version exists,
    prints a warning with the release URL. All network and parsing errors
    are caught and reported without interrupting execution.

    Args:
        current_version: The running version string (e.g., "1.3.0").

    """
    url = "https://api.github.com/repos/OlyoshaOlyosha/Project2Prompt/releases/latest"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
        tag_name: str = data.get("tag_name", "")
        if not tag_name:
            warning("Could not check for updates: missing tag in GitHub response.")
            return
        version_str = tag_name.lstrip("v")  # e.g., "v1.3.1" -> "1.3.1"
        current_tuple = _parse_version(current_version)
        latest_tuple = _parse_version(version_str)
        if latest_tuple > current_tuple:
            warning(
                f"A new version {tag_name} is available! "
                f"You are running v{current_version}. "
                f"Visit https://github.com/OlyoshaOlyosha/Project2Prompt/releases"
            )
    except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError, OSError) as e:
        warning(f"Could not check for updates: {e}")


def _parse_version(version: str) -> tuple[int, ...]:
    """Convert a dotted version string into a tuple of integers."""
    return tuple(int(part) for part in version.split("."))
