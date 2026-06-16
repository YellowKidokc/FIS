from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

RiskRank = {"low": 1, "medium": 2, "high": 3}

@dataclass
class RecipeCandidate:
    recipe_id: str
    recipe_type: str
    title: str
    subtitle: str
    one_sentence: str
    folder_path: str
    priority_score: float
    confidence: float
    risk: str
    source_blocks: list[str]
    primitives: list[str]
    suggested_actions: list[str]
    reason: str
    preview_endpoint: str | None = None

RECIPE_COPY = {
    "build_memory": ("Build folder memory", "Understand this folder before acting", "River can scan, summarize, and remember this folder without changing files."),
    "clean_duplicates": ("Clean duplicate clutter", "Review repeated copies first", "River found files that appear to be repeated copies. I recommend reviewing exact matches first and moving extras to a review folder, not deleting them."),
    "clean_names": ("Fix weak names", "Preview clearer names", "River found weak or generated names. I can preview cleaner names using this folder’s FolderBrain keywords before anything is renamed."),
    "sort_by_composition": ("Sort by composition", "Separate mixed file families", "This folder has mixed file families. I can separate the main family and send leftovers to review."),
    "separate_mixed_folder": ("Separate mixed folder", "Split unrelated material safely", "River sees mixed themes and can propose a split without moving anything until approval."),
    "build_similar_hub": ("Build a similar hub", "Link related folders without merging", "These folders appear related, but merging would be risky. I can create a hub page that links them without moving anything."),
    "archive_old_or_junk": ("Archive old or junk residue", "Move clutter to review, not delete", "River found old exports, residue, or temporary files. I can move them to an archive-review area so they leave active work without being deleted."),
    "create_folder_template": ("Create a folder template", "Add missing structure after approval", "River can create a small approved folder structure for repeatable work."),
    "review_low_confidence": ("Review uncertain classification", "Keep in place until confidence improves", "River is not confident enough to move this folder. I recommend reviewing what it is before any changes."),
    "create_automation_rule": ("Create an automation rule", "Only after repeated approvals", "River can turn repeated approved choices into a rule later; this stays disabled until enough evidence exists."),
}

PRIMITIVES = {
    "build_memory": ["scan", "folderbrain", "report"],
    "clean_duplicates": ["scan", "duplicates", "review", "archive", "report", "preference_learning"],
    "clean_names": ["scan", "folderbrain", "rename", "review", "report"],
    "sort_by_composition": ["scan", "folder_composition", "separate", "move", "folder_template", "review"],
    "separate_mixed_folder": ["scan", "folder_composition", "separate", "review"],
    "build_similar_hub": ["scan", "similarity", "link_hub", "report"],
    "archive_old_or_junk": ["scan", "archive", "delete_later", "review", "report"],
    "create_folder_template": ["scan", "folder_template", "create_folder", "review"],
    "review_low_confidence": ["scan", "classification", "review", "report"],
    "create_automation_rule": ["preference_learning", "automation", "review"],
}

ASK_RULES = [
    (("duplicate", "copy", "copies", "clutter"), ["clean_duplicates"]),
    (("rename", "names", "named", "easier to find", "find"), ["clean_names", "build_similar_hub", "create_folder_template"]),
    (("sort", "type", "composition", "separate", "organize"), ["sort_by_composition", "separate_mixed_folder"]),
    (("hub", "related", "link", "combine"), ["build_similar_hub"]),
    (("archive", "old", "junk", "residue", "cleanup"), ["archive_old_or_junk"]),
    (("don't move", "do not move", "tell me", "what it is", "understand"), ["build_memory", "review_low_confidence", "build_similar_hub"]),
]

def to_dict(recipe: RecipeCandidate) -> dict[str, Any]: return asdict(recipe)

def ask_river_recipe_types(text: str) -> list[str]:
    q = (text or "").lower(); found: list[str] = []
    for needles, recipes in ASK_RULES:
        if any(n in q for n in needles):
            for r in recipes:
                if r not in found: found.append(r)
    return found or ["build_memory"]

def _block(blocks: list[dict], *types: str) -> list[dict]: return [b for b in blocks if b.get("block_type") in types]
def _risk(blocks: list[dict]) -> str:
    risks = [b.get("risk", "low") for b in blocks]
    return max(risks or ["low"], key=lambda r: RiskRank.get(r, 1))
def _score(confidence: float, cleanup_value: float, risk: str, affected: int, intent: bool = False, reversible: bool = True, ambiguity: bool = False) -> float:
    return round(confidence * 40 + cleanup_value * 20 + min(affected, 25) * 0.8 + (10 if reversible else 0) + (15 if intent else 0) - (RiskRank.get(risk, 1)-1)*12 - (12 if ambiguity else 0), 2)

def _candidate(recipe_type: str, folder_path: str, blocks: list[dict], confidence: float, cleanup_value: float, reason: str, actions: list[str], intent_types: list[str]) -> RecipeCandidate:
    title, subtitle, sentence = RECIPE_COPY[recipe_type]
    source = [b.get("block_id") for b in blocks if b.get("block_id")]
    affected = sum(int(b.get("item_count", 0) or 0) for b in blocks)
    risk = _risk(blocks)
    return RecipeCandidate(f"{recipe_type}_{abs(hash((folder_path, tuple(source)))) % 100000:05d}", recipe_type, title, subtitle, sentence, folder_path, _score(confidence, cleanup_value, risk, affected, recipe_type in intent_types, recipe_type not in {"sort_by_composition", "archive_old_or_junk"}, recipe_type == "review_low_confidence"), confidence, risk, source, PRIMITIVES[recipe_type], actions, reason, "/api/storyboard/build")

def build_recipe_candidates(scan_result: dict | None, folder_path: str, user_intent: str | None = None) -> list[RecipeCandidate]:
    intent_types = ask_river_recipe_types(user_intent or "") if user_intent else []
    if not scan_result:
        return [_candidate("build_memory", folder_path, [], 0.9, 0.2, "No scan result is cached yet; start by building memory.", ["scan_folder"], intent_types)]
    blocks = scan_result.get("review_blocks", [])
    brain = scan_result.get("folderbrain", {}) or {}
    recipes: list[RecipeCandidate] = []
    safety = _block(blocks, "safety")
    if safety: recipes.append(_candidate("build_memory", folder_path, safety, 0.95, 0.2, "Safety/protected-path evidence should be understood first.", ["review_summary"], intent_types))
    dupes = _block(blocks, "duplicates", "near_duplicates")
    if dupes: recipes.append(_candidate("clean_duplicates", folder_path, dupes, max(b.get("confidence", 0.8) for b in dupes), 0.95, "Exact or near duplicate evidence exists; duplicate review is high-confidence and reversible.", ["review_duplicates", "archive_extra_copy", "ignore_group"], intent_types))
    renames = _block(blocks, "rename")
    if renames: recipes.append(_candidate("clean_names", folder_path, renames, max(b.get("confidence", 0.7) for b in renames), 0.75, "Weak or generated filenames can be previewed before any rename.", ["preview_names", "edit_pattern", "approve_rename_plan"], intent_types))
    low_conf = bool((brain.get("classification") or {}).get("needs_review") or (brain.get("route") or {}).get("keep_in_place"))
    if low_conf: recipes.append(_candidate("review_low_confidence", folder_path, _block(blocks, "classification", "move_keep"), 0.65, 0.3, "Classification confidence is low, so River recommends review and keep-in-place.", ["review_summary", "keep_in_place"], intent_types))
    tiny_or_template = _block(blocks, "tiny_folder", "folder_template", "large_files")
    if tiny_or_template: recipes.append(_candidate("sort_by_composition", folder_path, tiny_or_template, 0.68, 0.45, "Tiny folders or composition signals suggest a safe organization preview.", ["preview_template", "create_missing_folders", "skip_template"], intent_types))
    similar = _block(blocks, "similar_hub")
    if similar: recipes.append(_candidate("build_similar_hub", folder_path, similar, 0.72, 0.5, "Similar folders are better linked than merged.", ["find_similar", "create_hub_page", "link_dont_move"], intent_types))
    junk = _block(blocks, "junk_residue", "large_files")
    if junk: recipes.append(_candidate("archive_old_or_junk", folder_path, junk, 0.62, 0.45, "Residue can be moved to archive review, never deleted.", ["review_junk", "archive_residue", "skip_cleanup"], intent_types))
    recipes.append(_candidate("create_folder_template", folder_path, _block(blocks, "folder_template"), 0.5, 0.2, "A template can be previewed if you want more structure.", ["preview_template", "create_missing_folders", "skip_template"], intent_types))
    recipes.append(_candidate("create_automation_rule", folder_path, [], 0.25, 0.1, "Automation requires repeated approved decisions first.", ["save_preference", "create_rule"], intent_types))
    if intent_types:
        existing = {r.recipe_type for r in recipes}
        for recipe_type in intent_types:
            if recipe_type not in existing:
                recipes.append(_candidate(recipe_type, folder_path, [], 0.5, 0.2, "Added from Ask River request.", ["build_storyboard"], intent_types))
    return sorted(recipes, key=lambda r: r.priority_score, reverse=True)
