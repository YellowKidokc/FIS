from __future__ import annotations
import time
from pathlib import Path
from typing import Any
from core.models import Finding, to_dict
from core import review_blocks
from engines import classifier, clusters, duplicates, folderbrain as folderbrain_engine, inventory, naming, router, similarity

ENGINE_ORDER = [duplicates, naming, classifier, router, similarity, clusters]

def _cache_call(cache: Any, name: str, *args):
    try:
        fn = getattr(cache, name, None)
        if callable(fn): fn(*args)
    except Exception:
        pass

def _inventory_findings(scan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if scan.get("tiny_folders"):
        findings.append(Finding("tiny_folder_001", "inventory", "tiny_folder", "Tiny folders found", "Folders with 0-2 direct files may be fragments or empty residue.", items=scan["tiny_folders"], confidence=0.82, risk="medium", weight=5, suggested_actions=["merge_candidates", "archive_empty", "keep_as_protected"], evidence={"threshold": "<=2 direct files"}))
    if scan.get("large_files"):
        findings.append(Finding("large_files_001", "inventory", "large_file", "Large files found", "Large files may be space users and should be reviewed before archive decisions.", items=scan["large_files"], confidence=0.9, risk="low", weight=3, suggested_actions=["review_large_files", "archive_large_files", "keep_in_place"], evidence={"method": "size threshold"}))
    if scan.get("skipped_folders"):
        findings.append(Finding("safety_skipped_001", "inventory", "safety", "Protected/generated folders skipped", "River skipped protected or generated folders during read-only inventory.", items=[{"name": k, "count": v} for k, v in scan["skipped_folders"].items()], confidence=1.0, risk="low", weight=10, suggested_actions=["protect_folder", "continue_review"], evidence={"policy": "default excludes"}))
    return findings

def run_folder_intelligence(folder_path: str, options: dict | None = None) -> dict:
    started = time.perf_counter(); timings = {}; warnings: list[str] = []
    path = Path(folder_path).expanduser()
    if not path.exists():
        return {"error": f"Folder does not exist: {folder_path}", "folderbrain": None, "findings": [], "review_blocks": [], "warnings": [], "timing": {}}
    if not path.is_dir():
        return {"error": f"Path is not a folder: {folder_path}", "folderbrain": None, "findings": [], "review_blocks": [], "warnings": [], "timing": {}}
    t = time.perf_counter(); scan = inventory.scan(str(path), options); timings["inventory"] = round(time.perf_counter() - t, 4); warnings.extend(scan.get("warnings", []))
    cache = {"inventory": scan}
    t = time.perf_counter(); brain = folderbrain_engine.build(str(path), cache, scan); timings["folderbrain"] = round(time.perf_counter() - t, 4)
    findings: list[Finding] = _inventory_findings(scan)
    for engine in ENGINE_ORDER:
        t = time.perf_counter()
        try:
            engine_findings = engine.analyze(brain, cache, options) or []
            findings.extend(engine_findings)
        except Exception as exc:
            warnings.append(f"{engine.__name__} failed: {exc}")
        timings[engine.__name__.split('.')[-1]] = round(time.perf_counter() - t, 4)
    brain.findings = [to_dict(f) for f in findings]
    t = time.perf_counter(); blocks = review_blocks.build(brain, findings); timings["review_blocks"] = round(time.perf_counter() - t, 4)
    timings["total"] = round(time.perf_counter() - started, 4)
    return {"folderbrain": to_dict(brain), "findings": to_dict(findings), "review_blocks": to_dict(blocks), "warnings": warnings, "timing": timings}
