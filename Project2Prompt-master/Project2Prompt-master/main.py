"""
Project2Prompt - Main module.

This module provides the entry point for exporting code projects to a single file for AI review.
"""

import argparse
import ast
import importlib.util
import time
from pathlib import Path
from typing import Any

from exporter.console import error, header, info, prompt, warning
from exporter.processor import export_project
from exporter.updater import check_for_updates
from exporter.utils import OutputInfo, get_next_filename, print_statistics, select_directory


def load_app_config() -> dict[str, bool]:
    """Load application-level configuration from app_config.py next to main.py.

    Returns:
        Dictionary with 'check_for_updates' key (bool). Defaults to True
        if the file is missing or cannot be loaded.

    """
    config_path = Path(__file__).parent / "app_config.py"
    if not config_path.is_file():
        return {"check_for_updates": True}

    # Dynamically load the module
    spec = importlib.util.spec_from_file_location("app_config", config_path)
    if spec is None or spec.loader is None:
        warning(f"Could not load app config module from {config_path}. Using defaults.")
        return {"check_for_updates": True}

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as e:
        # SyntaxError, permission errors, etc.
        warning(f"Failed to execute app_config.py: {e}. Using defaults.")
        return {"check_for_updates": True}

    value = getattr(module, "CHECK_FOR_UPDATES", True)
    return {"check_for_updates": bool(value)}


def _get_config_description(config_path: Path) -> str | None:
    """Extract a short user-friendly description from a config file using static AST parsing.

    Looks for a top-level assignment: CONFIG_DESCRIPTION = "..." and returns
    the first non-empty line, truncated to 77 characters with an ellipsis
    if longer. Returns None if the variable is missing, not a string, or
    the file cannot be read/parsed.

    Args:
        config_path: Path to the configuration .py file.

    Returns:
        Truncated description string or None.

    """
    try:
        source = config_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            # Only consider a single target named CONFIG_DESCRIPTION
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            if node.targets[0].id != "CONFIG_DESCRIPTION":
                continue
            # Value must be a string constant
            if not isinstance(node.value, ast.Constant) or not isinstance(node.value.value, str):
                return None
            raw = node.value.value
            # Extract first non-empty line
            lines = raw.split("\n")
            first_line = next((line.strip() for line in lines if line.strip()), "")
            if not first_line:
                return None
            if len(first_line) > 77:
                return first_line[:77] + "..."
            return first_line
        return None
    except Exception:
        # Any error (missing file, permission, syntax, etc.) → no description
        return None


def _display_config_tree(config_files: list[Path]) -> None:
    """Display configuration files as a directory tree with continuous numbering.

    The tree is printed to stdout. Files are numbered in the order they appear
    in *config_files*, which must already be sorted deterministically.

    Args:
        config_files: The sorted list of ``.py`` config paths found by
                      ``find_config_files()``.

    """
    configs_dir = Path("configs")

    # Collect descriptions once, outside the rendering loop.
    descriptions: dict[Path, str | None] = {}
    for path in config_files:
        descriptions[path] = _get_config_description(path)

    # Build a tree of nested dicts from relative paths.
    # Keys are directory names; '__files__' holds a list of
    # (display_name, full_path, description).
    tree: dict = {}
    for path in config_files:
        rel = path.relative_to(configs_dir)
        parts = rel.parts
        display_name = path.stem  # filename without .py

        node = tree
        for part in parts[:-1]:  # directories leading to the file
            if part not in node:
                node[part] = {}
            node = node[part]

        if "__files__" not in node:
            node["__files__"] = []
        node["__files__"].append((display_name, path, descriptions[path]))

    # Recursive renderer – mutates *counter_ref* (a 1‑element list) so the
    # numbering is continuous across the whole tree.
    def render_node(node: dict, prefix: str = "", counter_ref: list[int] | None = None) -> None:
        if counter_ref is None:
            counter_ref = [1]

        dirs = sorted([k for k in node if k != "__files__"])
        files = sorted(node.get("__files__", []), key=lambda x: x[0])  # sort by display name

        items = dirs + files  # directories first, then files
        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            pointer = "└── " if is_last else "├── "

            if isinstance(item, str):  # directory
                print(f"{prefix}{pointer}{item}/")
                extension = "    " if is_last else "│   "
                render_node(node[item], prefix + extension, counter_ref)
            else:  # file: (display_name, path, desc)
                display, _path, desc = item
                number = counter_ref[0]
                counter_ref[0] += 1
                if desc:
                    print(f"{prefix}{pointer}{number}. {display} – {desc}")
                else:
                    print(f"{prefix}{pointer}{number}. {display}")

    render_node(tree)


def find_config_files() -> list[Path]:
    """Return a sorted list of .py config files from the 'configs/' directory tree.

    Recursively searches subdirectories. Excludes any path whose components
    start with a dot, as well as ``__init__.py`` files.

    Returns:
        Sorted list of Path objects that matches the order used by
        ``_display_config_tree`` (subdirectory files first, root files last,
        alphabetical within groups). Returns empty list on error.

    """
    configs_dir = Path("configs")
    if not configs_dir.is_dir():
        return []

    try:
        valid_paths: list[Path] = []
        for p in configs_dir.rglob("*.py"):
            # Skip files whose relative path contains a hidden component
            if any(part.startswith(".") for part in p.relative_to(configs_dir).parts):
                continue
            if p.name == "__init__.py":
                continue
            valid_paths.append(p)
    except OSError as e:
        warning(f"Cannot read 'configs/' directory tree: {e}")
        return []

    # Sort to match the depth‑first numbering produced by _display_config_tree.
    # Directory components receive priority (0, name) over the final file
    # component (1, stem), so that all files in subdirectories appear before
    # root files, and each directory's own files come after its subdirectory
    # files.
    def _tree_sort_key(p: Path) -> tuple[tuple[int, str], ...]:
        rel = p.relative_to(configs_dir)
        parts = list(rel.parts)
        stem = p.stem  # file name without .py, as shown in the tree
        key: list[tuple[int, str]] = []
        for part in parts[:-1]:
            key.append((0, part))
        key.append((1, stem))
        return tuple(key)

    return sorted(valid_paths, key=_tree_sort_key)


def _resolve_config_path(name: str) -> Path | None:
    """Resolve a configuration name to an existing Path, without extension magic.

    Checks, in order:
      1. Absolute path (must exist).
      2. Relative path inside the ``configs/`` directory.
      3. Relative path from the current working directory.

    Args:
        name: The raw string supplied by the user (may or may not include ``.py``).

    Returns:
        A ``Path`` to the existing file, or ``None`` if nothing matches.

    """
    candidate = Path(name)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None

    candidate = Path("configs") / name
    if candidate.exists():
        return candidate

    candidate = Path(name)
    return candidate if candidate.exists() else None


def select_config_file(requested_config: str | None) -> Path | None:
    """Determine which configuration file to use.

    Priority:
        1. If --config is provided, use that file from 'configs/' (or as absolute path).
           Automatically appends ``.py`` if the raw input is not found as‑is and does not
           already end with ``.py``.
        2. Otherwise, look inside 'configs/':
            - If exactly one .py file, use it automatically.
            - If multiple, display a tree with continuous numbering and prompt the user.
        3. Fall back to root 'config.py' if 'configs/' is empty or missing.

    Args:
        requested_config: Value of the --config command-line argument.

    Returns:
        Path to the selected configuration file, or None if not found (should exit).

    """
    # 1. Explicit --config argument
    if requested_config:
        candidate = _resolve_config_path(requested_config)
        if candidate is not None:
            return candidate

        # If the user omitted the .py extension, try appending it as a fallback.
        if not requested_config.endswith(".py"):
            fallback = requested_config + ".py"
            candidate = _resolve_config_path(fallback)
            if candidate is not None:
                return candidate
            error(f"Configuration file not found: {requested_config} (also tried {fallback})")
        else:
            error(f"Configuration file not found: {requested_config}")
        return None

    # 2. Automatic selection from configs/
    config_files = find_config_files()
    if config_files:
        if len(config_files) == 1:
            # Show relative path without .py extension
            rel = config_files[0].relative_to(Path("configs"))
            if rel.parent != Path():
                display_name = f"{rel.parent.as_posix()}/{rel.stem}"
            else:
                display_name = rel.stem
            info(f"Using configuration: {display_name}")
            return config_files[0]

        # Multiple configs – display tree with continuous numbering
        _display_config_tree(config_files)
        while True:
            choice = prompt("Select configuration number: ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(config_files):
                    return config_files[idx]
            except ValueError:
                pass
            error("Invalid selection. Please enter a number from the list.")

    # 3. Fallback to root config.py
    root_config = Path("config.py")
    if root_config.exists():
        warning("No configurations found in 'configs/'. Falling back to root 'config.py'.")
        return root_config

    error(
        "No configuration file found. Please create 'configs/' folder with at least one .py file or 'config.py' in root."
    )
    return None


def load_config(config_path: Path) -> dict[str, Any]:
    """Dynamically load a configuration module from the given path.

    Args:
        config_path: Path to the .py configuration file.

    Returns:
        Dictionary containing the configuration values.

    Raises:
        SystemExit: If the file is missing, cannot be imported, or is incomplete.

    """
    if not config_path.exists():
        error(f"ERROR: Configuration file not found: {config_path}")
        info("Please ensure the configuration file exists.")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    # Dynamically import the module
    spec = importlib.util.spec_from_file_location("user_config", config_path)
    if spec is None or spec.loader is None:
        error(f"ERROR: Could not load configuration from {config_path}")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except SyntaxError as e:
        error(f"ERROR: Syntax error in configuration file: {e}")
        info("Tip: check for missing quotes or a backslash at the end of a raw string.")
        input("\nPress Enter to exit...")
        raise SystemExit(1)
    except Exception as e:
        error(f"ERROR: Failed to execute configuration file: {e}")
        input("\nPress Enter to exit...")
        raise SystemExit(1)

    required_attrs = {
        "BLACKLIST_EXTENSIONS": set,
        "BLACKLIST_DIRS": set,
        "BLACKLIST_FILENAMES": set,
        "FILENAME_FILTER_MODE": str,
        "OUTPUT_DIR": str,
        "OUTPUT_FILENAME": str,
        "MAX_FILE_SIZE_MB": (int, float),
        "CREATE_FILE": bool,
        "COPY_TO_CLIPBOARD": bool,
        "INCLUDE_EMPTY_FILES": bool,
        "EXPORT_STRUCTURE": bool,
        "EXPORT_CONTENT": bool,
        "SHOW_EMPTY_DIRS": bool,
        "MAX_CLIPBOARD_CHARS": int,
        "MAX_DEPTH": int,
        "USE_GITIGNORE": bool,
        "ALLOWED_EXTENSIONLESS_FILES": set,
    }

    config_dict = {}
    for attr, expected_type in required_attrs.items():
        if not hasattr(module, attr):
            # Provide defaults for optional settings (backward compatibility)
            if attr in ("USE_GITIGNORE", "ALLOWED_EXTENSIONLESS_FILES"):
                default = False if attr == "USE_GITIGNORE" else set()
                config_dict[attr.lower()] = default
                continue
            error(f"ERROR: Configuration file is missing required setting: {attr}")
            info("Please ensure the configuration contains all settings from the template.")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        value = getattr(module, attr)
        if not isinstance(value, expected_type):
            error(f"ERROR: Configuration setting {attr} has wrong type (expected {expected_type})")
            input("\nPress Enter to exit...")
            raise SystemExit(1)
        if attr == "MAX_DEPTH" and value < -1:
            error(
                f"ERROR: MAX_DEPTH is set to {value}. Valid range: -1 (unlimited), 0 (root only), or positive integer."
            )
            info("Please fix the value in your configuration file (MAX_DEPTH must be -1, 0, or a positive integer).")
            raise SystemExit(1)
        # Notify user about unlimited file size mode (0 = disabled limit)
        if attr == "MAX_FILE_SIZE_MB" and value == 0:
            info("MAX_FILE_SIZE_MB = 0 — file size limit disabled. All files will be included regardless of size.")
        config_dict[attr.lower()] = value

    # Transform keys and values to the internal format
    config_dict["max_size"] = config_dict.pop("max_file_size_mb") * 1024 * 1024
    config_dict["output_dir"] = config_dict.pop("output_dir")
    config_dict["default_output"] = config_dict.pop("output_filename")
    config_dict["create_file"] = config_dict.pop("create_file")
    config_dict["copy_to_buffer"] = config_dict.pop("copy_to_clipboard")
    config_dict["include_empty_files"] = config_dict.pop("include_empty_files")
    config_dict["export_structure"] = config_dict.pop("export_structure")
    config_dict["export_content"] = config_dict.pop("export_content")
    config_dict["show_empty_dirs"] = config_dict.pop("show_empty_dirs")
    config_dict["max_clipboard_chars"] = config_dict.pop("max_clipboard_chars")
    config_dict["max_depth"] = config_dict.pop("max_depth")
    config_dict["blacklist_extensions"] = config_dict.pop("blacklist_extensions")
    config_dict["blacklist_dirs"] = config_dict.pop("blacklist_dirs")
    config_dict["blacklist_filenames"] = config_dict.pop("blacklist_filenames")
    config_dict["filename_filter_mode"] = config_dict.pop("filename_filter_mode")

    # Optional input directory preset
    if hasattr(module, "INPUT_DIR"):
        raw_input = module.INPUT_DIR
        if not isinstance(raw_input, str):
            error("ERROR: INPUT_DIR must be a string.")
            raise SystemExit(1)
        config_dict["input_dir"] = raw_input.strip()
    else:
        config_dict["input_dir"] = ""

    # Optional priority sorting patterns
    for attr in ("PRIORITY_PATTERNS", "LOW_PRIORITY_PATTERNS"):
        if not hasattr(module, attr):
            config_dict[attr.lower()] = []
        else:
            value = getattr(module, attr)
            if not isinstance(value, list):
                error(f"ERROR: {attr} must be a list.")
                raise SystemExit(1)
            config_dict[attr.lower()] = value

    info(f"Configuration loaded from {config_path}")
    return config_dict


def check_export_options(config_dict: dict[str, Any]) -> dict[str, Any]:
    """Check and adjust export options for the current run.

    - If both file and clipboard outputs are disabled, enables file output.
    - If both structure and content exports are disabled, prompts the user
      to enable content export for this session only (no file modification).

    Args:
        config_dict: Configuration dictionary.

    Returns:
        The modified configuration dictionary, or an empty dict
        if the user chooses to exit.

    """
    create_file = config_dict["create_file"]
    copy_to_buffer = config_dict["copy_to_buffer"]

    if not create_file and not copy_to_buffer:
        create_file = True
        info("File output enabled (both outputs were disabled)")

    if not config_dict.get("export_structure", True) and not config_dict.get("export_content", True):
        warning("WARNING: Both EXPORT_STRUCTURE and EXPORT_CONTENT are disabled in configuration.")
        warning("Nothing will be exported!")
        response = (
            prompt(
                "Do you want to enable code export (EXPORT_CONTENT=True) for this run? (Press Enter for Yes, or type n and Enter to exit): "
            )
            .strip()
            .lower()
        )

        if response == "" or response.startswith("y"):
            config_dict["export_content"] = True
            info("Content export enabled for this run.\n")
        else:
            warning("Exiting — no content to export.")
            return {}

    config_dict["create_file"] = create_file
    config_dict["copy_to_buffer"] = copy_to_buffer
    return config_dict


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments once."""
    parser = argparse.ArgumentParser(description="Export code project to a single file for AI review")
    parser.add_argument("-o", "--output", help="Output file name")
    parser.add_argument("-d", "--directory", help="Path to the project directory")
    parser.add_argument(
        "-c", "--config", help="Name of the configuration file (e.g., 'python.py') from the 'configs/' folder"
    )
    return parser.parse_args()


def get_input_directory(args: argparse.Namespace, config_input_dir: str) -> str | None:
    """
    Determine input directory based on command line arguments, config preset, or user interaction.

    Priority: CLI argument > valid config preset > manual folder selection.

    Args:
        args: Parsed command line arguments.
        config_input_dir: Optional directory preset from the configuration file.

    Returns:
        Selected directory path or None if cancelled/invalid.

    """
    # 1. Command-line argument takes highest priority
    if args.directory:
        cli_dir = Path(args.directory).resolve()
        if not cli_dir.is_dir():
            error("The specified directory does not exist!")
            return None

        # Inform the user if a config preset was overridden
        if config_input_dir.strip():
            try:
                config_resolved = Path(config_input_dir).expanduser().resolve()
                # samefile() works cross-platform and is case-insensitive on Windows
                if not cli_dir.samefile(config_resolved):
                    info("Using directory from command line (-d). Ignoring INPUT_DIR from config.")
            except OSError:
                # config_resolved does not exist – definitely different
                info("Using directory from command line (-d). Ignoring INPUT_DIR from config.")
            except Exception:
                # Path is malformed; ignore comparison
                pass
        return str(cli_dir)

    # 2. No CLI argument: try the config preset
    if config_input_dir.strip():
        try:
            resolved = Path(config_input_dir).expanduser().resolve()
            if resolved.is_dir():
                return str(resolved)
            if resolved.exists():
                warning(
                    f"INPUT_DIR from config is a file, not a directory: {resolved}\n"
                    "Falling back to manual folder selection..."
                )
            else:
                warning(f"INPUT_DIR from config does not exist: {resolved}\nFalling back to manual folder selection...")
        except Exception:
            warning("INPUT_DIR from config caused an error. Falling back to manual folder selection...")

    # 3. Fallback to GUI or console folder selection
    info("Select the project folder...")
    dir_path = select_directory()
    if not dir_path:
        error("No folder selected!")
    return dir_path


def get_output_filename(
    args: argparse.Namespace,
    config: dict[str, Any],
    *,
    create_file: bool,
) -> str:
    """
    Determine output filename based on command line arguments and config.

    Args:
        args: Parsed command line arguments.
        config: Configuration dictionary.
        create_file: Whether the file will actually be written (skips uniqueness check if False).

    Returns:
        Output file path as string.

    """
    if args.output:
        # Use provided path, possibly prepend output_dir if relative
        path = Path(args.output)
        if not path.is_absolute():
            # Relative path: prepend output_dir from config
            base_dir = Path(config["output_dir"])
            path = base_dir / path
        return str(path)

    # No command line output specified: use OUTPUT_DIR / default_output
    base_dir = Path(config["output_dir"])
    candidate = base_dir / config["default_output"]

    # Only generate a unique filename if we actually intend to create the file
    if create_file:
        return get_next_filename(str(candidate))
    return str(candidate)


def perform_export(
    input_dir: str,
    output_file: str,
    config: dict[str, Any],
    *,
    create_file: bool,
    copy_to_buffer: bool,
) -> None:
    """Perform the export and print statistics."""
    info(f"Directory: {input_dir}")
    info(f"Output file: {output_file}")

    start_time = time.time()

    files_by_dir, total_chars, full_output, stats = export_project(
        input_dir, output_file, config, create_file=create_file, copy_to_buffer=copy_to_buffer
    )

    elapsed_time = time.time() - start_time
    output_info = OutputInfo(output_file, create_file, copy_to_buffer)
    print_statistics(
        files_by_dir,
        total_chars,
        elapsed_time,
        output_info,
        input_dir,
        full_output,
        stats=stats,
        show_empty_dirs=config.get("show_empty_dirs", False),
        blacklist_dirs=config.get("blacklist_dirs", set()),
    )


def main() -> None:
    __version__ = "1.4.0"
    __app_name__ = "Project2Prompt"

    try:
        header(f"{__app_name__} v{__version__}")

        args = parse_arguments()

        # 1. Choose configuration file
        config_path = select_config_file(args.config)
        if config_path is None:
            input("\nPress Enter to exit...")
            return

        # Capture the ordered list of configs (for later switching by number).
        # This list is only refreshed once; dynamic additions/removals are not
        # reflected until the next run.
        config_files = find_config_files()

        # Application-level settings (checked once)
        app_cfg = load_app_config()
        do_update_check = app_cfg.get("check_for_updates", True)
        if do_update_check:
            check_for_updates(__version__)

        # ── Helper to load (or reload) a configuration and apply stem ──────
        def _prepare_config(cfg_path: Path) -> dict[str, Any] | None:
            """Load config, append stem to output dir, and validate export options.

            Returns the config dict or None if the user chose to exit (e.g., when
            both export flags are disabled and the user refuses the override).
            """
            cfg = load_config(cfg_path)
            config_stem = cfg_path.stem
            base_out = Path(cfg["output_dir"])
            cfg["output_dir"] = str(base_out / config_stem)
            cfg = check_export_options(cfg)
            return cfg or None

        # ── First export ───────────────────────────────────────────────────
        config_dict = _prepare_config(config_path)
        if not config_dict:
            input("\nPress Enter to exit...")
            return

        input_dir = get_input_directory(args, config_dict.get("input_dir", ""))
        if not input_dir:
            input("\nPress Enter to exit...")
            return

        output_file = get_output_filename(args, config_dict, create_file=config_dict["create_file"])
        perform_export(
            input_dir,
            output_file,
            config_dict,
            create_file=config_dict["create_file"],
            copy_to_buffer=config_dict["copy_to_buffer"],
        )

        # ── Interactive re‑export / config switching loop ──────────────────
        while True:
            answer = prompt("\nExport again? (Enter — same config, number — switch config, N — exit): ").strip().lower()

            if answer == "":
                # Hot‑reload the *same* config from disk (picks up edits)
                config_dict = _prepare_config(config_path)
                if not config_dict:
                    break
                # Keep the same project directory – no re‑prompt
            elif answer.isdigit():
                idx = int(answer) - 1
                if 0 <= idx < len(config_files):
                    config_path = config_files[idx]
                    config_dict = _prepare_config(config_path)
                    if not config_dict:
                        break
                    # Switching to a different config → re‑determine directory
                    input_dir = get_input_directory(args, config_dict.get("input_dir", ""))
                    if not input_dir:
                        break
                else:
                    error("Invalid config number.")
                    continue
            elif answer == "n":
                break
            else:
                error("Invalid input. Press Enter, type a number, or N.")
                continue

            # (Re)compute output filename (always advances the counter)
            output_file = get_output_filename(args, config_dict, create_file=config_dict["create_file"])
            perform_export(
                input_dir,
                output_file,
                config_dict,
                create_file=config_dict["create_file"],
                copy_to_buffer=config_dict["copy_to_buffer"],
            )

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        return


if __name__ == "__main__":
    main()
