"""Utility functions for project export.

This module provides helper functions for directory selection, filename generation,
and statistics printing.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import tiktoken
from rich.table import Table
from rich.tree import Tree

from exporter.console import console, error, info, success, warning


def select_directory() -> str | None:
    """Prompt for a project directory via GUI or console fallback.

    First attempts a tkinter folder selection dialog. If tkinter is not available
    or fails, falls back to manual console input.

    Returns:
        The selected directory path or None if no selection was made.

    """
    # Attempt GUI selection
    folder_path = None
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import filedialog  # noqa: PLC0415
    except ImportError as e:
        warning(f"GUI folder selection unavailable: {e}")
    else:
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder_path = filedialog.askdirectory(title="Select project folder")
            root.destroy()
        except tk.TclError as e:
            warning(f"GUI folder selection unavailable: {e}")

    if folder_path:
        return folder_path

    # Fallback to manual input
    info("Please enter the project directory path manually:")
    while True:
        user_input = input("Path: ").strip()
        if not user_input:
            return None
        path = Path(user_input).expanduser().resolve()
        if path.is_dir():
            return str(path)
        error(f"Directory does not exist or is not accessible: {path}")
        info("Press Enter to cancel or try again.")


def get_next_filename(base_name: str) -> str:
    """Generate a unique filename by always appending a sequential number.

    Scans the parent directory once to find the highest existing numeric suffix,
    then returns the next number.

    Args:
        base_name: The base file path (e.g., "outputs/config/output.txt").

    Returns:
        A unique file path with a numeric suffix (e.g., "outputs/config/output_1.txt").

    """
    path = Path(base_name)
    parent = path.parent
    stem = path.stem
    suffix = path.suffix

    # Scan directory once to find the maximum existing counter
    max_counter = 0
    pattern = f"{stem}_"
    if parent.exists():
        for existing in parent.iterdir():
            name = existing.name
            if name.startswith(pattern) and name.endswith(suffix):
                # Extract the numeric part between pattern and suffix
                middle = name[len(pattern) : -len(suffix)]
                if middle.isdigit():
                    max_counter = max(max_counter, int(middle))

    counter = max_counter + 1
    return str(parent / f"{stem}_{counter}{suffix}")


@dataclass
class OutputInfo:
    """Information about output destination and actions."""

    output_file: str
    create_file: bool
    copy_to_buffer: bool


@dataclass
class ExportStats:
    """Statistics collected during project scanning.

    Attributes:
        skipped_binary: Number of files skipped because they could not be read (binary/unreadable).
        skipped_size: Number of files skipped because they exceeded the size limit.
        skipped_rules: Number of files skipped due to blacklist rules (extensions, names, directories).
        extension_counts: Mapping from file extension (without dot) to count of exported files.
        largest_files: List of (size_in_bytes, relative_path) tuples for the largest candidate files.

    """

    skipped_binary: int = 0
    skipped_size: int = 0
    skipped_rules: int = 0
    extension_counts: dict[str, int] = field(default_factory=dict)
    largest_files: list[tuple[int, str]] = field(default_factory=list)


def print_statistics(
    files_by_dir: dict[str, list[str]],
    total_chars: int,
    elapsed_time: float,
    output_info: OutputInfo,
    input_dir: str,
    full_output: str,
    stats: ExportStats | None = None,
    *,
    show_empty_dirs: bool = False,
    blacklist_dirs: set[str] | None = None,
) -> None:
    """Print formatted statistics after export.

    Order: file tree → basic metrics (time, chars, tokens, dirs/files) →
    extended statistics (skips, extension table, largest files) → final result.
    """
    num_dirs = len(files_by_dir)
    num_files = sum(len(files) for files in files_by_dir.values())
    root_name = Path(input_dir).name

    enc = tiktoken.get_encoding("o200k_base")
    token_count = len(enc.encode(full_output))

    if total_chars >= 1024 * 1024:
        size_str = f"{total_chars / (1024 * 1024):.2f} MB"
    else:
        size_str = f"{total_chars / 1024:.1f} KB"

    # ── 1. File tree (moved above statistics) ──
    info("\nFiles by directory:")

    # Collect all known directories (from exported files + empty ones from disk)
    all_dirs: set[str] = set(files_by_dir.keys())

    if show_empty_dirs and blacklist_dirs is not None:
        input_path = Path(input_dir)
        for dirpath, dirnames, _ in os.walk(input_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in blacklist_dirs]
            rel = Path(dirpath).relative_to(input_path).as_posix()
            for d in dirnames:
                accumulated = f"{rel}/{d}" if rel != "." else d
                all_dirs.add(accumulated)

    tree = Tree(f"[blue]{root_name}/[/]", guide_style="bold bright_blue")
    dir_nodes: dict[str, Tree] = {".": tree}

    # Build tree in sorted order — directories first, then files
    for rel_dir in sorted(all_dirs):
        parts = rel_dir.split("/")
        accumulated = ""
        parent_node = tree
        for part in parts:
            accumulated = f"{accumulated}/{part}" if accumulated else part
            if accumulated not in dir_nodes:
                dir_node = parent_node.add(f"[blue]{part}/[/]")
                dir_nodes[accumulated] = dir_node
            parent_node = dir_nodes[accumulated]

        # Add any files that belong to this directory
        for filename in sorted(files_by_dir.get(rel_dir, [])):
            parent_node.add(filename)

    console.print(tree)

    # ── 2. Statistics block ──
    info("=== STATISTICS ===")

    # Elapsed time colour thresholds
    time_style = "green" if elapsed_time < 1.0 else ("yellow" if elapsed_time < 5.0 else "red")
    info(f"Elapsed time: [{time_style}]{elapsed_time:.2f} sec[/]")

    info(f"Characters: {total_chars:,} ({size_str})")

    # Token colour thresholds
    context_limit = 128_000
    percentage = (token_count / context_limit) * 100
    if percentage < 50:
        token_style = "green"
    elif percentage < 80:
        token_style = "yellow"
    elif percentage < 95:
        token_style = "bright_yellow"
    else:
        token_style = "red"
    info(f"Tokens: ~[{token_style}]{token_count:,}[/] / {context_limit:,} ({percentage:.1f}%)")

    info(f"📁 Directories: {num_dirs}")
    info(f"📄 Files: {num_files}")

    # ── 3. Extended statistics (only when stats is provided and we have enough files) ──
    if stats is not None and num_files > 10:
        # --- Skip summary (print only non‑zero counters) ---
        skip_lines = []
        if stats.skipped_binary > 0:
            skip_lines.append(f"⚠️ Binary / unreadable: {stats.skipped_binary}")
        if stats.skipped_size > 0:
            skip_lines.append(f"⚖️ Exceeded size limit: {stats.skipped_size}")
        if stats.skipped_rules > 0:
            skip_lines.append(f"❌ Excluded by rules: {stats.skipped_rules}")
        if skip_lines:
            info("")
            for line_text in skip_lines:
                info(line_text)

        # --- Top Extensions table ---
        if stats.extension_counts:
            sorted_exts = sorted(stats.extension_counts.items(), key=lambda item: item[1], reverse=True)[:10]
            ext_table = Table(title="Top Extensions")
            ext_table.add_column("Extension", justify="left")
            ext_table.add_column("Count", justify="right")
            ext_table.add_column("%", justify="right")
            for ext, count in sorted_exts:
                pct = (count / num_files) * 100 if num_files else 0.0
                ext_table.add_row(ext, str(count), f"{pct:.1f}%")
            info("")
            console.print(ext_table)

        # --- Top‑5 largest files ---
        if stats.largest_files:
            sorted_large = sorted(stats.largest_files, key=lambda x: x[0], reverse=True)[:5]

            def _format_size(size: int) -> str:
                """Return a human‑readable size string."""
                if size >= 1024 * 1024:
                    return f"{size / 1048576:.1f} MB"
                if size >= 1024:
                    return f"{size / 1024:.1f} KB"
                return f"{size} B"

            large_table = Table(title="Top 5 Largest Files")
            large_table.add_column("File", justify="left")
            large_table.add_column("Size", justify="right")
            for file_size, file_path in sorted_large:
                large_table.add_row(file_path, _format_size(file_size))
            info("")
            console.print(large_table)

    # ── 4. Final result line ──
    result_parts = []
    if output_info.create_file:
        result_parts.append(f"saved to {output_info.output_file}")
    if output_info.copy_to_buffer:
        result_parts.append("copied to clipboard")

    success(f"\nDone! Result: {' and '.join(result_parts)}")
