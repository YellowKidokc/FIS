from __future__ import annotations
from collections import defaultdict
from core.models import Finding, ReviewBlock

BLOCK_MAP = {
    "folderbrain_summary": ("folderbrain_summary", "FolderBrain Summary", 6, ["review_summary", "edit_domain", "write_folderbrain"]),
    "theme_detection": ("theme_detection", "Theme Detection", 6, ["find_themes", "create_theme_groups", "mark_mixed_folder"]),
    "safety": ("safety", "Risk / Safety Check", 10, ["protect_folder", "protect_file_types", "continue_review"]),
    "exact_duplicate": ("duplicates", "Duplicate Review", 9, ["review_duplicates", "archive_extra_copy", "ignore_group"]),
    "same_name_same_size": ("duplicates", "Duplicate Review", 7, ["review_duplicates", "ignore_group"]),
    "near_duplicate": ("near_duplicates", "Duplicate Review", 8, ["review_duplicates", "archive_extra_copy", "ignore_group"]),
    "rename_candidates": ("rename", "Rename Scheme", 8, ["preview_names", "edit_pattern", "approve_rename_plan"]),
    "rename": ("rename", "Rename Scheme", 8, ["preview_names", "edit_pattern", "approve_rename_plan"]),
    "classification": ("classification", "Classification Review", 7, ["accept_domain", "choose_different_domain", "split_by_theme"]),
    "route_recommendation": ("move_keep", "Move / Keep Decision", 8, ["keep_in_place", "move_as_unit", "split_folder"]),
    "tiny_folder": ("tiny_folder", "Tiny Folder Review", 5, ["merge_candidates", "archive_empty", "keep_as_protected"]),
    "empty_folder": ("tiny_folder", "Tiny Folder Review", 5, ["merge_candidates", "archive_empty", "keep_as_protected"]),
    "large_file": ("large_files", "Large Files Review", 3, ["review_large_files", "archive_large_files", "keep_in_place"]),
    "junk_residue": ("junk_residue", "Junk / Residue Review", 7, ["review_junk", "archive_residue", "skip_cleanup"]),
    "similar_hub": ("similar_hub", "Similar Hubs", 6, ["find_similar", "create_hub_page", "link_dont_move"]),
    "folder_template": ("folder_template", "Folder Template", 4, ["preview_template", "create_missing_folders", "skip_template"]),
    "learn_preference": ("learn_preference", "Learn Preference", 4, ["save_preference", "create_rule", "reset_learning"]),
}
REQUIRED_DEMO_BLOCKS = ["folderbrain_summary", "theme_detection", "safety", "duplicates", "tiny_folder", "junk_residue", "classification", "move_keep", "similar_hub", "rename", "folder_template", "learn_preference"]

def build(folderbrain, findings: list[Finding]) -> list[ReviewBlock]:
    synthetic = [Finding("folderbrain_summary_001", "folderbrain", "folderbrain_summary", "FolderBrain Summary", getattr(folderbrain, "summary", "Review folder summary."), confidence=0.9, risk="low", weight=6, suggested_actions=["review_summary", "edit_domain", "write_folderbrain"], evidence={"folder_id": getattr(folderbrain, "folder_id", None)}), Finding("theme_detection_001", "folderbrain", "theme_detection", "Theme Detection", "Review detected extension/domain themes before splitting anything.", confidence=0.65, risk="low", weight=6, suggested_actions=["find_themes", "create_theme_groups", "mark_mixed_folder"], evidence={"top_extensions": getattr(folderbrain, "top_extensions", {})}), Finding("folder_template_001", "folderbrain", "folder_template", "Folder Template", "Optional template suggestions require preview and approval.", confidence=0.5, risk="low", weight=4, suggested_actions=["preview_template", "create_missing_folders", "skip_template"], evidence={}), Finding("learn_preference_001", "preference", "learn_preference", "Learn Preference", "Decisions can train River preferences after review.", confidence=0.5, risk="low", weight=4, suggested_actions=["save_preference", "create_rule", "reset_learning"], evidence={})]
    all_findings = [*synthetic, *findings]
    grouped = defaultdict(list)
    for finding in all_findings:
        grouped[BLOCK_MAP.get(finding.finding_type, (finding.finding_type or "conflict", finding.title or "Review", finding.weight, finding.suggested_actions))[0]].append(finding)
    blocks: list[ReviewBlock] = []
    for block_type, found in grouped.items():
        mapped = BLOCK_MAP.get(found[0].finding_type, (block_type, found[0].title, found[0].weight, found[0].suggested_actions))
        title, default_weight = mapped[1], mapped[2]
        actions = sorted({a for f in found for a in (f.suggested_actions or mapped[3] or [])})
        items = [item for f in found for item in f.items]
        engines = sorted({f.engine for f in found})
        summary = " ".join(f.summary for f in found if f.summary)[:700]
        blocks.append(ReviewBlock(f"{block_type}-001", block_type, title, summary, max([f.weight for f in found] + [default_weight]), max((f.risk for f in found), key={"low": 1, "medium": 2, "high": 3}.get), round(sum(f.confidence for f in found) / max(len(found), 1), 3), len(items), items, actions, {"engines": engines, "finding_ids": [f.finding_id for f in found], "active": bool(items) or block_type in {"classification", "move_keep", "safety", "folderbrain_summary"}}))
    return sorted(blocks, key=lambda b: (-b.weight, b.block_type))
