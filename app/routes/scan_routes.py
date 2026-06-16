"""Scan route contract for the stdlib River server.

These modules intentionally do not own HTTP dispatch yet; app.server is the current
compatibility server. Keeping endpoint metadata here documents the future split and
prevents route placeholders from being empty rooms.
"""

ENDPOINTS = {
    "POST /api/scan": "Run the real folder-intelligence orchestrator for a path.",
    "GET /api/scan": "Legacy UI compatibility wrapper for query-string scans.",
    "GET /api/cache/scan": "Legacy cache scan alias; preview/read-only only.",
}
