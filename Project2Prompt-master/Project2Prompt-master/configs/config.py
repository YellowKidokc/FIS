"""
User configuration for Project2Prompt.

Edit this file to customize filtering and behavior.
"""

# Brief description of this configuration (one line, ~80 chars max).
# It will be shown in the configuration selection menu.
CONFIG_DESCRIPTION = "Default configuration – all file types, balanced filters"

# File extensions to ignore (without dot)
BLACKLIST_EXTENSIONS = {
    "txt", "md", "markdown", "log", "pdf", "doc", "docx", "xls", "xlsx",
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "svg", "webp",
    "mp3", "mp4", "avi", "mov", "wav",
    "zip", "rar", "7z", "tar", "gz",
    "exe", "dll", "so", "bin", "o", "obj",
    "pyc", "pyo", "pyd", "class",
    "db", "sqlite", "mdb",
    "ini", "cfg", "conf", "config", "env",
    # Build artifacts and generated files
    "pyi",            # Type stub files
    "lock",           # Dependency lock files (poetry.lock, package-lock.json)
    "map",            # Source maps
}

# Extensionless files whitelist
# Files without a file extension are normally excluded. Add names here to allow them.
ALLOWED_EXTENSIONLESS_FILES = {
    "Dockerfile",
    "Makefile",
    "README",
    "LICENSE",
}

# Directories to completely skip
BLACKLIST_DIRS = {
    "__pycache__",
    ".git",
    ".vscode",
    ".vs",
    ".idea",
    "node_modules",
    "obj",
    "bin",
    "venv",
    "env",
    "virtualenv",
    "dist",
    "build",
    "target",
    "packages",
    # Caches and test outputs
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "htmlcov",
    "coverage",
    # Temporary directories
    "tmp",
    "temp",
    "logs",
}

# To exclude minified/bundled files (e.g., app.min.js, vendor.bundle.js),
# add them here and set FILENAME_FILTER_MODE = "contains".
# Example: BLACKLIST_FILENAMES = {"min.", "bundle.", "chunk."}
# Note: do NOT add these to BLACKLIST_EXTENSIONS -- that set works on the
# part after the LAST dot, so "min.js" would only match a file named literally "min.js".
BLACKLIST_FILENAMES = {"setup.py", "requirements.txt"}

# Filename matching mode: 'exact' or 'contains'
FILENAME_FILTER_MODE = "exact"

# Default project directory to export.
# Can be an absolute path, e.g.:
#   Windows:  "C:\\Users\\Name\\Projects\\MyApp"
#   Linux/macOS: "/home/name/Projects/MyApp"
# You can also use "~" to refer to the home directory, e.g. "~/Projects/MyApp".
# Leave empty ("") to always prompt for folder selection (GUI or console).
INPUT_DIR: str = ""

# Output settings
OUTPUT_DIR = "outputs"  # Default directory for output files
OUTPUT_FILENAME = "output.txt"  # Base name for output file (will be placed in OUTPUT_DIR)
# Max file size to include (in MB). Set to 0 to disable the limit.
MAX_FILE_SIZE_MB = 5
CREATE_FILE = True  # Write output to file
COPY_TO_CLIPBOARD = True  # Copy output to clipboard

# Export options
EXPORT_STRUCTURE = True  # Include project directory tree in output
EXPORT_CONTENT = True  # Include file contents (code) in output

SHOW_EMPTY_DIRS = True  # Include empty directories in the structure tree
INCLUDE_EMPTY_FILES = True  # Include empty files in output (structure only, no empty code blocks)

# Clipboard safety
MAX_CLIPBOARD_CHARS = 500000  # Maximum characters to copy to clipboard (0 to disable)

# Directory traversal depth
MAX_DEPTH = -1  # -1 = unlimited, 0 = only selected directory, positive integer = max depth

# .gitignore integration
USE_GITIGNORE = True  # If True, also respect .gitignore rules (in addition to blacklists)

# Priority-based file ordering (optional).
# Patterns use fnmatch syntax against the entire relative path.
# Within each priority tier files are sorted by directory depth then alphabetically.
# When both lists are empty the original insertion order is preserved.
#
# Example for a typical Python project:
# PRIORITY_PATTERNS: list[str] = [
#     "README*",
#     "*.yaml", "*.yml", "*.toml", "setup.cfg", "pyproject.toml",
#     "src/*.py", "src/*/*.py", "tests/*.py", "*.py",
# ]
# LOW_PRIORITY_PATTERNS: list[str] = [
#     "requirements*.txt", "Pipfile", "Pipfile.lock",
# ]
PRIORITY_PATTERNS: list[str] = []
LOW_PRIORITY_PATTERNS: list[str] = []
