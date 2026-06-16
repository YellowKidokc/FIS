"""FolderBrain route contract for River FIS."""

ENDPOINTS = {
    "GET /api/folderbrain": "Build and return FolderBrain JSON from real scan data.",
    "GET /api/cache/folderbrain": "Legacy alias for FolderBrain preview.",
    "POST /api/folderbrain/write": "Create a dry-run write_folderbrain ActionPlan; does not write directly.",
}
