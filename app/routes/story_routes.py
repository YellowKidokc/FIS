"""Recipe and storyboard route contract for River FIS Story Mode."""

ENDPOINTS = {
    "GET /api/recipes": "Return ranked RecipeCandidate objects for a folder.",
    "GET /api/recipes/next": "Return the single recommended next recipe for a folder.",
    "POST /api/storyboard/build": "Build a readable storyboard and dry-run plan from a recipe.",
    "GET /api/storyboard": "Return a stored storyboard by id.",
    "POST /api/storyboard/decision": "Record approve/edit/skip/defer without executing files.",
}
