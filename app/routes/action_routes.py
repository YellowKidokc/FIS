"""Action-plan route contract for River FIS."""

ENDPOINTS = {
    "POST /api/action/plan": "Create a dry-run, unapproved ActionPlan from a review decision.",
    "POST /api/action/preview": "Return plan steps and safety result; never mutates files.",
    "POST /api/action/approve": "Mark a stored plan approved for a later execute call.",
    "POST /api/action/execute": "Execute only approved, non-dry-run plans that pass safety.",
}
