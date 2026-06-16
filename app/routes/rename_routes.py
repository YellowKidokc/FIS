"""Rename route contract for River FIS."""

ENDPOINTS = {
    "GET /api/rename/preview": "Return rename candidate findings/previews only.",
    "GET /api/rename/baseline-plan": "Legacy baseline plan alias; preview-only.",
    "GET /api/cache/rename-plan": "Legacy cache rename plan alias; preview-only.",
    "GET /api/cache/rename-sample": "Legacy rename sample alias; preview-only.",
}
