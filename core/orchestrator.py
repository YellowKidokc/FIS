from __future__ import annotations
import time
from pathlib import Path
from typing import Any, Callable
from core.models import Finding, to_dict
from core import review_blocks
from engines import chi_evaluator, classifier, clusters, domain_chi, duplicates, folderbrain as folderbrain_engine, inventory, naming, nlp_bridge, router, similarity

ENGINE_ORDER = [duplicates, naming, classifier, router, similarity, clusters, nlp_bridge, domain_chi, chi_evaluator]

def _cache_call(cache: Any, name: str, *args):
    try:
        fn = getattr(cache, name, None)
        if callable(fn):
            fn(*args)
            return None
    except Exception as exc:
        return str(exc)
    return None

def _inventory_findings(scan: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if scan.get("tiny_folders"):
        findings.append(Finding("tiny_folder_001", "inventory", "tiny_folder", "Tiny folders found", "Folders with 0-2 direct files may be fragments or empty residue.", items=scan["tiny_folders"], confidence=0.82, risk="medium", weight=5, suggested_actions=["merge_candidates", "archive_empty", "keep_as_protected"], evidence={"threshold": "<=2 direct files"}))
    if scan.get("large_files"):
        findings.append(Finding("large_files_001", "inventory", "large_file", "Large files found", "Large files may be space users and should be reviewed before archive decisions.", items=scan["large_files"], confidence=0.9, risk="low", weight=3, suggested_actions=["review_large_files", "archive_large_files", "keep_in_place"], evidence={"method": "size threshold"}))
    if scan.get("zero_byte_files"):
        findings.append(Finding("zero_byte_001", "inventory", "zero_byte_file", "Zero-byte files found", "Empty files often indicate broken exports, aborted saves, or placeholder artifacts that should be reviewed.", items=scan["zero_byte_files"], confidence=0.93, risk="medium", weight=7, suggested_actions=["review_zero_byte_files", "archive_residue", "keep_in_place"], evidence={"count": len(scan["zero_byte_files"])}))
    if scan.get("odd_files"):
        findings.append(Finding("odd_file_001", "inventory", "odd_file_type", "Odd file type outliers found", "A small number of files do not match the dominant folder pattern and should be reviewed before River assumes they belong.", items=scan["odd_files"], confidence=0.76, risk="medium", weight=6, suggested_actions=["review_outliers", "keep_in_place", "split_by_theme"], evidence={"dominant_domain": scan.get("dominant_domain"), "domain_counts": scan.get("domain_counts", {})}))
    if scan.get("skipped_folders"):
        findings.append(Finding("safety_skipped_001", "inventory", "safety", "Protected/generated folders skipped", "River skipped protected or generated folders during read-only inventory.", items=[{"name": k, "count": v} for k, v in scan["skipped_folders"].items()], confidence=1.0, risk="low", weight=10, suggested_actions=["protect_folder", "continue_review"], evidence={"policy": "default excludes"}))
    return findings

def run_folder_intelligence(
    folder_path: str,
    options: dict | None = None,
    progress_callback: Callable[[dict[str, Any]], None] | None = None,
) -> dict:
    def progress(stage: str, label: str, **extra: Any) -> None:
        if progress_callback is None:
            return
        payload = {"stage": stage, "label": label}
        payload.update(extra)
        progress_callback(payload)

    started = time.perf_counter(); timings = {}; warnings: list[str] = []
    path = Path(folder_path).expanduser()
    if not path.exists():
        return {"error": f"Folder does not exist: {folder_path}", "folderbrain": None, "findings": [], "review_blocks": [], "warnings": [], "timing": {}}
    if not path.is_dir():
        return {"error": f"Path is not a folder: {folder_path}", "folderbrain": None, "findings": [], "review_blocks": [], "warnings": [], "timing": {}}
    progress("inventory", "Scanning folder inventory", current=1, total=len(ENGINE_ORDER) + 4)
    t = time.perf_counter(); scan = inventory.scan(str(path), options); timings["inventory"] = round(time.perf_counter() - t, 4); warnings.extend(scan.get("warnings", []))
    cache = (options or {}).get("cache") if isinstance(options, dict) else None
    memory_cache = {"inventory": scan}
    if cache is not None:
        cache_warning = _cache_call(cache, "store_inventory", scan)
        if cache_warning: warnings.append(f"cache.store_inventory failed: {cache_warning}")
    progress("inventory_complete", "Inventory complete", current=2, total=len(ENGINE_ORDER) + 4, files=scan.get("file_count"), folders=scan.get("folder_count"))
    t = time.perf_counter(); brain = folderbrain_engine.build(str(path), memory_cache, scan); timings["folderbrain"] = round(time.perf_counter() - t, 4)
    progress("folderbrain", "Building FolderBrain summary", current=3, total=len(ENGINE_ORDER) + 4)
    findings: list[Finding] = _inventory_findings(scan)
    total_steps = len(ENGINE_ORDER) + 4
    for idx, engine in enumerate(ENGINE_ORDER, start=4):
        t = time.perf_counter()
        progress(engine.__name__.split('.')[-1], f"Running {engine.__name__.split('.')[-1]}", current=idx, total=total_steps)
        try:
            engine_findings = engine.analyze(brain, memory_cache, options) or []
            findings.extend(engine_findings)
        except Exception as exc:
            warnings.append(f"{engine.__name__} failed: {exc}")
        timings[engine.__name__.split('.')[-1]] = round(time.perf_counter() - t, 4)
    brain.findings = [to_dict(f) for f in findings]
    if cache is not None:
        cache_warning = _cache_call(cache, "store_findings", brain.findings)
        if cache_warning: warnings.append(f"cache.store_findings failed: {cache_warning}")
    progress("review_blocks", "Building review blocks", current=total_steps, total=total_steps)
    t = time.perf_counter(); blocks = review_blocks.build(brain, findings); timings["review_blocks"] = round(time.perf_counter() - t, 4)
    timings["total"] = round(time.perf_counter() - started, 4)
    progress("complete", "Scan complete", current=total_steps, total=total_steps, findings=len(findings), review_blocks=len(blocks))
    return {"folderbrain": to_dict(brain), "findings": to_dict(findings), "review_blocks": to_dict(blocks), "warnings": warnings, "timing": timings}
