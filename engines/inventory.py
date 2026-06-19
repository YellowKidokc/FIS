from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

DEFAULT_EXCLUDES = {".git", ".venv", "venv", "env", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache", "dist", "build", "_gsdata_"}
LARGE_FILE_BYTES = 100 * 1024 * 1024
DOMAIN_EXTENSIONS = {
    "code": {".py", ".js", ".jsx", ".ts", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".md", ".bat", ".ps1"},
    "documents": {".txt", ".pdf", ".doc", ".docx", ".rtf", ".xls", ".xlsx", ".csv", ".tsv", ".ppt", ".pptx"},
    "media": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tiff", ".mp4", ".mov", ".mp3", ".wav"},
    "archives": {".zip", ".7z", ".rar", ".tar", ".gz"},
}


def _domain_for_ext(ext: str) -> str:
    for domain, extensions in DOMAIN_EXTENSIONS.items():
        if ext in extensions:
            return domain
    return "other"

def _is_skipped(path: Path, excludes: set[str]) -> str | None:
    for part in path.parts:
        if part.lower() in excludes:
            return part
    return None

def scan(folder_path: str, options: dict | None = None) -> dict[str, Any]:
    opts = options or {}
    root = Path(folder_path).expanduser()
    warnings: list[str] = []
    if not root.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")
    root = root.resolve()
    excludes = {x.lower() for x in opts.get("exclude_names", DEFAULT_EXCLUDES)}
    max_files = int(opts.get("max_files", 50000))
    large_threshold = int(opts.get("large_file_bytes", LARGE_FILE_BYTES))
    files: list[dict[str, Any]] = []
    folders: list[dict[str, Any]] = []
    ext_counts: Counter[str] = Counter()
    child_counts: defaultdict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "folders": 0})
    folder_file_counts: Counter[str] = Counter()
    skipped: Counter[str] = Counter()
    total_size = 0
    zero_byte_files: list[dict[str, Any]] = []
    domain_counts: Counter[str] = Counter()

    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(current.iterdir())
        except OSError as exc:
            warnings.append(f"Cannot read {current}: {exc}")
            continue
        for entry in entries:
            skip = _is_skipped(entry, excludes)
            if skip:
                skipped[skip] += 1
                continue
            try:
                is_dir = entry.is_dir() if not entry.is_symlink() else False
                is_file = entry.is_file() if not entry.is_symlink() else False
            except OSError as exc:
                warnings.append(f"Cannot inspect {entry}: {exc}")
                continue
            rel_parts = entry.relative_to(root).parts
            top_child = rel_parts[0] if rel_parts else entry.name
            if is_dir:
                folders.append({"path": str(entry), "name": entry.name, "parent": str(entry.parent)})
                child_counts[top_child]["folders"] += 1
                stack.append(entry)
            elif is_file:
                if len(files) >= max_files:
                    warnings.append(f"File limit reached at {max_files}; scan truncated")
                    continue
                try:
                    stat = entry.stat()
                except OSError as exc:
                    warnings.append(f"Cannot stat {entry}: {exc}")
                    continue
                ext = entry.suffix.lower() or "[none]"
                total_size += stat.st_size
                ext_counts[ext] += 1
                domain = _domain_for_ext(ext)
                domain_counts[domain] += 1
                child_counts[top_child]["files"] += 1
                folder_file_counts[str(entry.parent)] += 1
                row = {"path": str(entry), "name": entry.name, "parent": str(entry.parent), "ext": entry.suffix.lower(), "size": stat.st_size, "mtime": stat.st_mtime, "domain": domain}
                files.append(row)
                if stat.st_size == 0:
                    zero_byte_files.append(row)
            else:
                warnings.append(f"Skipped non-regular path: {entry}")
    tiny = []
    folder_paths = {f["path"] for f in folders}
    for fpath in folder_paths:
        count = folder_file_counts.get(fpath, 0)
        if count <= int(opts.get("tiny_folder_file_limit", 2)):
            tiny.append({"path": fpath, "file_count": count})
    large = [f for f in files if f["size"] >= large_threshold]
    dominant_domain = domain_counts.most_common(1)[0][0] if domain_counts else "other"
    odd_files = []
    dominant_total = domain_counts.get(dominant_domain, 0)
    if dominant_total >= max(8, int(len(files) * 0.6)):
        for row in files:
            if row["domain"] != dominant_domain and domain_counts.get(row["domain"], 0) <= 3:
                odd_files.append(row)
    return {
        "folder_path": str(root),
        "folder_name": root.name,
        "root": str(root),
        "files": files,
        "folders": folders,
        "file_count": len(files),
        "folder_count": len(folders),
        "total_size": total_size,
        "extension_counts": dict(ext_counts),
        "top_extensions": dict(ext_counts.most_common(20)),
        "top_level_child_counts": dict(child_counts),
        "tiny_folders": tiny,
        "large_files": large,
        "zero_byte_files": zero_byte_files[:50],
        "odd_files": odd_files[:50],
        "domain_counts": dict(domain_counts),
        "dominant_domain": dominant_domain,
        "skipped_folders": dict(skipped),
        "warnings": warnings,
    }
