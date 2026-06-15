from __future__ import annotations
from collections import Counter
from pathlib import Path

DEFAULT_EXCLUDES = {".git", ".venv", "venv", "node_modules", "__pycache__", "_gsdata_"}

def scan(folder_path: str, options: dict | None = None) -> dict:
    root = Path(folder_path).expanduser().resolve()
    max_files = int((options or {}).get("max_files", 10000))
    files, folders, ext_counts = [], [], Counter()
    for path in root.rglob("*"):
        if any(part in DEFAULT_EXCLUDES for part in path.parts):
            continue
        if path.is_dir():
            folders.append(str(path))
            continue
        if len(files) >= max_files:
            break
        try:
            stat = path.stat()
        except OSError:
            continue
        ext_counts[path.suffix.lower() or "[none]"] += 1
        files.append({"path": str(path), "name": path.name, "parent": str(path.parent), "ext": path.suffix.lower(), "size": stat.st_size, "mtime": stat.st_mtime})
    tiny = [{"path": f, "file_count": len([p for p in Path(f).iterdir() if p.is_file()])} for f in folders[:1000] if Path(f).exists()]
    return {"root": str(root), "files": files, "folders": folders, "file_count": len(files), "folder_count": len(folders), "top_extensions": dict(ext_counts.most_common(20)), "tiny_folders": [t for t in tiny if t["file_count"] <= 2]}
