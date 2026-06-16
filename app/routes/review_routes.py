"""Review route contract for River FIS."""

ENDPOINTS = {
    "GET /api/review/blocks": "Return ReviewBlock cards built from real findings.",
    "GET /api/review/block": "Return one cached ReviewBlock by id.",
    "POST /api/review/decide": "Record an approve/reject/defer/protect decision without executing file operations.",
    "POST /api/review/defer": "Record a deferred decision without execution.",
    "POST /api/review/protect": "Record a protected decision without execution.",
    "POST /api/findings/decide": "Legacy UI compatibility decision endpoint.",
}
