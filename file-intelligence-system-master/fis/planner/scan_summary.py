"""Read-only filesystem scanner for FIS preview planning."""
from __future__ import annotations

import hashlib, os
from collections import Counter, defaultdict
from uuid import uuid4
from .safety_rules import is_protected

SCANS: dict[str, dict] = {}


def scan_path(root: str, max_hash_bytes: int = 1024 * 1024) -> dict:
    if not root or not os.path.exists(root):
        raise FileNotFoundError(root or "path required")
    scan_id = str(uuid4())
    files = folders = total = protected = unknown = anomalies = 0
    ext_counts = Counter()
    size_hash = defaultdict(list)
    findings = {"duplicates": [], "anomalies": [], "protected": [], "folders": []}
    for cur, dirs, filenames in os.walk(root):
        folders += len(dirs)
        if len(findings["folders"]) < 200:
            findings["folders"].append({"path": cur, "folder_count": len(dirs), "file_count": len(filenames)})
        for name in filenames:
            path = os.path.join(cur, name)
            files += 1
            try:
                stat = os.stat(path)
                size = stat.st_size
            except OSError:
                unknown += 1
                continue
            total += size
            ext = os.path.splitext(name)[1].lower() or "[none]"
            ext_counts[ext] += 1
            if is_protected(path):
                protected += 1
                if len(findings["protected"]) < 200:
                    findings["protected"].append({"path": path, "reason": "protected type/name"})
            if not ext or ext == "[none]" or any(ch in name for ch in ['?', '*', ':', '"', '<', '>', '|']):
                anomalies += 1
                if len(findings["anomalies"]) < 200:
                    findings["anomalies"].append({"path": path, "reason": "missing or suspicious name/extension"})
            if size > 0:
                try:
                    h = hashlib.sha256()
                    with open(path, "rb") as fh:
                        h.update(fh.read(max_hash_bytes))
                    size_hash[(size, h.hexdigest())].append(path)
                except OSError:
                    unknown += 1
    for (size, digest), paths in size_hash.items():
        if len(paths) > 1:
            findings["duplicates"].append({"size_bytes": size, "hash": digest, "paths": paths[:25], "count": len(paths)})
    duplicate_groups = len(findings["duplicates"])
    most_common_type = ext_counts.most_common(1)[0][0] if ext_counts else ""
    summary = {
        "scan_id": scan_id, "root": root, "files_scanned": files, "folders_scanned": folders,
        "total_size_bytes": total, "duplicate_groups": duplicate_groups, "naming_anomalies": anomalies,
        "protected_count": protected, "unknown_count": unknown, "most_common_type": most_common_type,
        "findings": findings,
    }
    SCANS[scan_id] = summary
    return summary


def get_scan(scan_id: str) -> dict | None:
    return SCANS.get(scan_id)
