from __future__ import annotations
import hashlib, re
from pathlib import Path
from typing import Iterable

def content_hash(path: str | Path, chunk_size: int = 1024 * 1024) -> str | None:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            for chunk in iter(lambda: handle.read(chunk_size), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None

def normalized_name(name: str) -> str:
    stem = Path(name).stem.lower()
    stem = re.sub(r"\b(copy|final|v\d+|\(\d+\))\b", "", stem)
    stem = re.sub(r"[^a-z0-9]+", "", stem)
    return stem

def text_fingerprint(path: str | Path, max_chars: int = 20000) -> set[str]:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")[:max_chars].lower()
    except OSError:
        return set()
    words = re.findall(r"[a-z0-9]{3,}", text)
    return {" ".join(words[i:i+5]) for i in range(max(0, len(words)-4))}

def jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb: return 0.0
    return len(sa & sb) / len(sa | sb)
