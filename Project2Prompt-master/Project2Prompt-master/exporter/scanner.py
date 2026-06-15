"""Module for scanning and filtering code files based on blacklist rules."""

from pathlib import Path
from typing import Any


def is_code_file(file_path: str, config: dict[str, Any]) -> bool:
    """Determine if a file should be included in the export based on filters.

    Args:
        file_path: Path to the file to check.
        config: Configuration dictionary containing the keys:
            'blacklist_extensions', 'blacklist_dirs', 'blacklist_filenames',
            'filename_filter_mode', and optionally 'max_size'.

    Returns:
        True if the file should be included, False otherwise.

    """
    path = Path(file_path)
    filename = path.name

    # Skip hidden files
    if filename.startswith("."):
        return False

    # Filename blacklist (combined exact/contains check)
    blacklist_filenames = config["blacklist_filenames"]
    mode = config["filename_filter_mode"]
    if (mode == "exact" and filename in blacklist_filenames) or (
        mode == "contains" and any(p in filename for p in blacklist_filenames)
    ):
        return False

    # Skip if parent directory is blacklisted
    if path.parent.name in config["blacklist_dirs"]:
        return False

    # Skip files without extension or with blacklisted extension
    blacklist_extensions = config["blacklist_extensions"]
    ext = path.suffix.lower().lstrip(".")
    if not ext:
        # Extensionless file: include only if its name is in the whitelist
        allowed_extensionless = config.get("allowed_extensionless_files", set())
        if filename not in allowed_extensionless:
            return False
    elif ext in blacklist_extensions:
        return False

    # File size limit – return True only if size is within limit (or no limit)
    max_size = config.get("max_size")
    if max_size:
        try:
            if path.stat().st_size > max_size:
                return False
        except OSError as e:
            # File may be inaccessible or a broken symlink – skip it
            from exporter.console import warning

            warning(f"Skipping inaccessible file: {file_path} ({e})")
            return False
    return True
