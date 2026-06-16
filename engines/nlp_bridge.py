from __future__ import annotations
# Optional lazy bridge: importing this module must not load model weights.
def analyze(folderbrain, cache=None, options=None):
    if not (options or {}).get("use_nlp"):
        return []
    return []
