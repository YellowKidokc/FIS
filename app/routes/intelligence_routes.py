"""Intelligence/legacy compatibility route contract for River FIS."""

ENDPOINTS = {
    "GET /api/fingerprint": "Legacy fingerprint tool endpoint; compatibility response unless fully wired.",
    "GET /api/folders/compare": "Legacy compare endpoint; compatibility response unless fully wired.",
    "GET /api/folders/composition": "Legacy composition endpoint; compatibility response unless fully wired.",
    "POST /api/nlp-classify": "Optional NLP compatibility endpoint; never loads models on startup.",
}
