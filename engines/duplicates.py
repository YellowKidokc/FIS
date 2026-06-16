from __future__ import annotations
from collections import defaultdict
from core.models import Finding
from engines.fingerprint import content_hash, normalized_name, text_fingerprint, jaccard

TEXT_EXTS = {".txt", ".md", ".html", ".htm", ".py", ".js", ".jsx", ".css", ".json", ".yaml", ".yml"}

def analyze(folderbrain, cache=None, options=None) -> list[Finding]:
    opts = options or {}
    files = list(folderbrain.inventory.get("files", []))
    findings: list[Finding] = []
    by_hash = defaultdict(list)
    for item in files[: int(opts.get("max_hash_files", 2000))]:
        digest = content_hash(item["path"])
        if digest: by_hash[digest].append(item)
    exact = [group for group in by_hash.values() if len(group) > 1]
    if exact:
        findings.append(Finding("dup_exact_001", "duplicates", "exact_duplicate", "Exact duplicate files found", "Files with identical SHA-256 hashes need review before archiving extras.", items=[{"files": group, "count": len(group)} for group in exact], confidence=0.98, risk="medium", weight=9, suggested_actions=["review_duplicates", "archive_extra_copy", "ignore_group"], evidence={"method": "sha256"}))
    by_name_size = defaultdict(list)
    for item in files:
        by_name_size[(normalized_name(item["name"]), item.get("size", 0))].append(item)
    candidates = [group for (name, size), group in by_name_size.items() if name and size and len(group) > 1]
    if candidates:
        findings.append(Finding("dup_same_name_size_001", "duplicates", "same_name_same_size", "Same-name same-size duplicate candidates", "Files with similar normalized names and identical sizes may be duplicates.", items=[{"files": group, "count": len(group)} for group in candidates], confidence=0.82, risk="low", weight=7, suggested_actions=["review_duplicates", "ignore_group"], evidence={"method": "normalized_name+size"}))
    text_files = [f for f in files if f.get("ext") in TEXT_EXTS and f.get("size", 0) <= int(opts.get("near_duplicate_max_bytes", 2_000_000))][:200]
    fps = [(f, text_fingerprint(f["path"])) for f in text_files]
    near = []
    threshold = float(opts.get("near_duplicate_threshold", 0.88))
    for idx, (left, lfp) in enumerate(fps):
        for right, rfp in fps[idx + 1:]:
            score = jaccard(lfp, rfp)
            if score >= threshold:
                near.append({"files": [left, right], "score": round(score, 3)})
    if near:
        findings.append(Finding("dup_near_text_001", "duplicates", "near_duplicate", "Near-duplicate text files found", "Text fingerprints are highly similar and should be reviewed.", items=near, confidence=0.85, risk="medium", weight=8, suggested_actions=["review_duplicates", "archive_extra_copy", "ignore_group"], evidence={"method": "word-shingle-jaccard", "threshold": threshold}))
    return findings
