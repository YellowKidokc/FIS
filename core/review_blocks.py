from __future__ import annotations
from collections import defaultdict
from core.models import Finding, ReviewBlock

BLOCK_MAP = {
    "exact_duplicate": ("duplicates", "Duplicate Review", 9, ["review_duplicates", "archive_extra_copy", "ignore_group"]),
    "near_duplicate": ("near_duplicates", "Near Duplicate Review", 8, ["review_duplicates", "archive_extra_copy", "ignore_group"]),
    "rename": ("rename", "Rename Scheme", 8, ["preview_names", "edit_pattern", "approve_rename_plan"]),
    "bad_name": ("rename", "Rename Scheme", 8, ["preview_names", "edit_pattern", "approve_rename_plan"]),
    "classification": ("classification", "Classification Review", 7, ["accept_domain", "choose_different_domain", "split_by_theme"]),
    "tiny_folder": ("tiny_folder", "Tiny Folder Review", 5, ["merge_candidates", "archive_empty", "keep_as_protected"]),
    "empty_folder": ("tiny_folder", "Tiny Folder Review", 5, ["merge_candidates", "archive_empty", "keep_as_protected"]),
    "large_file": ("large_files", "Large Files Review", 3, ["review_large_files", "archive_large_files", "keep_in_place"]),
    "junk_residue": ("junk_residue", "Junk / Residue Review", 7, ["review_junk", "archive_residue", "skip_cleanup"]),
    "safety": ("safety", "Risk / Safety Check", 10, ["protect_folder", "protect_file_types", "continue_review"]),
    "similar_hub": ("similar_hub", "Similar Hubs", 6, ["find_similar", "create_hub_page", "link_dont_move"]),
}

def build(folderbrain, findings: list[Finding]) -> list[ReviewBlock]:
    grouped = defaultdict(list)
    for finding in findings:
        block_type, title, default_weight, actions = BLOCK_MAP.get(
            finding.finding_type,
            (finding.finding_type or "conflict", finding.title or "Review", finding.weight, finding.suggested_actions),
        )
        grouped[block_type].append((finding, title, default_weight, actions))
    blocks: list[ReviewBlock] = []
    for block_type, rows in grouped.items():
        found = [r[0] for r in rows]
        title = rows[0][1]
        actions = sorted({a for _, _, _, acts in rows for a in (acts or [])})
        items = [item for f in found for item in f.items]
        engines = sorted({f.engine for f in found})
        blocks.append(ReviewBlock(
            block_id=f"{block_type}-001", block_type=block_type, title=title,
            summary=" ".join(f.summary for f in found if f.summary)[:500],
            weight=max([f.weight for f in found] + [rows[0][2]]),
            risk=max((f.risk for f in found), key={"low": 1, "medium": 2, "high": 3}.get),
            confidence=round(sum(f.confidence for f in found) / max(len(found), 1), 3),
            item_count=len(items), items=items, suggested_actions=actions,
            evidence={"engines": engines, "finding_ids": [f.finding_id for f in found]},
        ))
    return sorted(blocks, key=lambda b: (-b.weight, b.block_type))
