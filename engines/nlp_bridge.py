"""Bridge to the local NLP box (X:\\NLP_BOX). FIS holds no models or model code.

Rules:
- Importing this module loads nothing (no torch, no weights).
- Nothing runs unless options["use_nlp"] is truthy.
- If the box is missing or fails, analyze() returns an "nlp_status" finding; the scan keeps going.
- Suggest-only: findings carry proposals; nothing is renamed, moved or written.

Transport: the box's own venv runs backside/worker.py's run() in one child process per scan
(all jobs on stdin, results on stdout), so FIS's Python never imports torch and models load once.
If that venv is missing, jobs go to inbox/ and outbox/<id>.json is awaited (needs START.bat).

Options: nlp_box (path), nlp_python (venv python), nlp_timeout (s), nlp_max_files,
nlp_snippet_chars, nlp_dedup_threshold, nlp_labels, nlp_transport ("auto"|"subprocess"|"inbox").
Env overrides: NLP_BOX, NLP_BOX_PYTHON.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import uuid
from pathlib import Path

from core.models import Finding

DEFAULT_BOX = r"X:\NLP_BOX"
DEFAULT_PYTHON = str(Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".nlp_box" / "venv" / "Scripts" / "python.exe")
TEXT_EXTS = {".txt", ".md", ".html", ".htm", ".py", ".js", ".jsx", ".css", ".json", ".yaml", ".yml", ".rst", ".csv"}
# FIS domains (folderbrain.DOMAIN_EXTENSIONS + classifier.KEYWORDS), phrased for zero-shot.
DOMAIN_LABELS = {
    "code": "software source code",
    "documents": "written document or notes",
    "data": "tabular data or records",
    "media": "media description or captions",
    "finance": "finance, trading or markets",
    "course": "course, lesson or training material",
}
MARK = "@@NLP_RESULT@@"

_RUNNER = """
import json, sys
sys.path.insert(0, sys.argv[1])
jobs = json.loads(sys.stdin.buffer.read().decode("utf-8"))
out = []
try:
    import worker
    err = None
except Exception as exc:
    worker, err = None, f"{type(exc).__name__}: {exc}"
for job in jobs:
    try:
        if worker is None:
            raise RuntimeError(err)
        out.append({"ok": True, "result": worker.run(job)})
    except Exception as exc:
        out.append({"ok": False, "error": f"{type(exc).__name__}: {exc}"})
sys.stdout.write(chr(10) + "MARK" + json.dumps(out))
""".replace("MARK", MARK)


class BoxUnavailable(RuntimeError):
    pass


def _call_subprocess(box: Path, python: str, jobs: list[dict], timeout: float) -> list[dict]:
    proc = subprocess.run([python, "-c", _RUNNER, str(box / "backside")], input=json.dumps(jobs).encode("utf-8"),
                          capture_output=True, timeout=timeout, cwd=str(box / "backside"))
    out = proc.stdout.decode("utf-8", "replace")
    if MARK not in out:
        raise BoxUnavailable(f"worker exited {proc.returncode}: {proc.stderr.decode('utf-8', 'replace')[-400:]}")
    return json.loads(out.rsplit(MARK, 1)[1])


def _call_inbox(box: Path, job: dict, timeout: float) -> dict:
    jid = f"fis-{uuid.uuid4().hex[:12]}"
    tmp = box / "inbox" / f"{jid}.tmp"
    tmp.write_text(json.dumps({"id": jid, **job}), encoding="utf-8")
    tmp.rename(tmp.with_suffix(".json"))
    out = box / "outbox" / f"{jid}.json"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if out.exists():
            try:
                res = json.loads(out.read_text(encoding="utf-8"))
            except ValueError:
                time.sleep(0.3)
                continue
            return {"ok": bool(res.get("ok")), "result": res.get("result"), "error": res.get("error")}
        time.sleep(0.5)
    return {"ok": False, "error": f"no answer in outbox within {timeout}s (is NLP_BOX START.bat running?)"}


def call_many(jobs: list[dict], options: dict | None = None) -> list[dict]:
    """Run NLP_BOX jobs ({"task", "input"}); returns [{"ok", "result"|"error"}] in order.
    Raises BoxUnavailable (or TimeoutExpired) if the box can't be reached at all."""
    opts = options or {}
    box = Path(opts.get("nlp_box") or os.environ.get("NLP_BOX") or DEFAULT_BOX)
    if not (box / "backside" / "worker.py").exists():
        raise BoxUnavailable(f"NLP box not found at {box}")
    python = opts.get("nlp_python") or os.environ.get("NLP_BOX_PYTHON") or DEFAULT_PYTHON
    timeout = float(opts.get("nlp_timeout", 900))
    transport = opts.get("nlp_transport", "auto")
    if transport == "inbox" or (transport == "auto" and not Path(python).exists()):
        return [_call_inbox(box, job, timeout) for job in jobs]
    return _call_subprocess(box, python, jobs, timeout)


def call(task: str, inp: dict, options: dict | None = None) -> object:
    """Run one NLP_BOX tool; raises BoxUnavailable on failure."""
    res = call_many([{"task": task, "input": inp}], options)[0]
    if not res.get("ok"):
        raise BoxUnavailable(res.get("error") or "unknown error")
    return res["result"]


def _snippet(path: str, limit: int) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return " ".join(fh.read(limit * 2).split())[:limit]
    except OSError:
        return ""


def _labels(opts) -> dict:
    labels = opts.get("nlp_labels") or DOMAIN_LABELS
    return {l: l for l in labels} if isinstance(labels, (list, tuple)) else dict(labels)


def _semantic_dupes(files, res, opts) -> list[Finding]:
    groups = [g for g in res.get("groups", []) if len(g.get("members", [])) > 1]
    if not groups:
        return []
    items = [{"files": [files[i] for i in g["members"]], "count": len(g["members"])} for g in groups]
    return [Finding("dup_semantic_nlp_001", "nlp_bridge", "near_duplicate_semantic", "Files that say the same thing",
                    "NLP_BOX embeddings put these files' opening text in the same meaning group. Review before archiving any copy.",
                    items=items, confidence=0.8, risk="medium", weight=8,
                    suggested_actions=["review_duplicates", "archive_extra_copy", "ignore_group"],
                    evidence={"method": "nlp_box:dedup (MiniLM cosine)", "threshold": res.get("threshold"),
                              "compared_with": "word-shingle-jaccard in duplicates.py"})]


def _topics(files, res, opts) -> list[Finding]:
    labels = _labels(opts)
    phrase_to_domain = {v: k for k, v in labels.items()}
    items, tally = [], {}
    for f, scores in zip(files, res):
        phrase, score = max(scores.items(), key=lambda kv: kv[1])
        dom = phrase_to_domain.get(phrase, phrase)
        tally[dom] = tally.get(dom, 0) + 1
        items.append({**f, "content_domain": dom, "score": score,
                      "scores": {phrase_to_domain.get(k, k): v for k, v in scores.items()}})
    top = max(tally, key=tally.get) if tally else "mixed"
    return [Finding("content_topic_nlp_001", "nlp_bridge", "content_topic", "Content topic per file",
                    f"Zero-shot reading of file text: most files look like {top}. Compare with the extension-based classification.",
                    items=items, confidence=0.7, risk="low", weight=6,
                    suggested_actions=["accept_domain", "choose_different_domain", "split_by_theme"],
                    evidence={"method": "nlp_box:zeroshot", "labels": labels, "tally": tally,
                              "compared_with": "classifier.py (extensions + filename keywords)"})]


def _names(files, res, opts) -> list[Finding]:
    from engines import naming  # cheap, no models
    items = []
    for f, phrases in zip(files, res):
        words = list(dict.fromkeys(w for p in phrases[:3] for w in naming.slugify(p["phrase"]).split("-") if w))
        if not words:
            continue
        ext = f.get("ext") or Path(f["name"]).suffix.lower()
        proposed = "-".join(words[:5])[:60].strip("-") + ext
        if proposed.lower() == f["name"].lower():
            continue
        items.append({**f, "reasons": naming._reasons(f.get("name", "")) or ["content_keyphrases"],
                      "keyphrases": phrases, "proposed_name": proposed, "proposed_scheme": "content-keyphrases"})
    if not items:
        return []
    items.sort(key=lambda i: i["reasons"] == ["content_keyphrases"])  # weak names (naming.py's rules) first
    return [Finding("rename_from_content_nlp_001", "nlp_bridge", "rename_candidates", "Names suggested from file content",
                    "KeyBERT key phrases from each file's text, as name proposals alongside naming.py's folder-keyword names. Preview only.",
                    items=items[:100], confidence=0.65, risk="medium", weight=6,
                    suggested_actions=["preview_names", "edit_pattern", "approve_rename_plan"],
                    evidence={"method": "nlp_box:keyphrases (KeyBERT)", "dry_run": True})]


def analyze(folderbrain, cache=None, options=None):
    opts = options or {}
    if not opts.get("use_nlp"):
        return []
    limit = int(opts.get("nlp_max_files", 200))
    chars = int(opts.get("nlp_snippet_chars", 1500))
    files, texts = [], []
    for f in folderbrain.inventory.get("files", []):
        if len(files) >= limit:
            break
        if (f.get("ext") or "").lower() not in TEXT_EXTS or not f.get("size"):
            continue
        text = _snippet(f["path"], chars)
        if len(text) >= 40:
            files.append(f)
            texts.append(text)
    if not files:
        return []
    steps = [
        (_semantic_dupes, {"task": "dedup", "input": {"texts": texts, "threshold": float(opts.get("nlp_dedup_threshold", 0.80))}}),
        (_topics, {"task": "zeroshot", "input": {"texts": texts, "labels": list(_labels(opts).values())}}),
        (_names, {"task": "keyphrases", "input": {"texts": texts, "top": 5}}),
    ]
    findings, errors = [], []
    try:
        results = call_many([job for _, job in steps], opts)
    except Exception as exc:  # box missing, timeout, crash: never break the scan
        results, errors = [], [f"{type(exc).__name__}: {exc}"]
    for (step, job), res in zip(steps, results):
        try:
            if not res.get("ok"):
                raise BoxUnavailable(res.get("error") or "unknown error")
            findings.extend(step(files, res["result"], opts))
        except Exception as exc:
            errors.append(f"{job['task']}: {exc}")
    if errors:
        findings.append(Finding("nlp_unavailable_001", "nlp_bridge", "nlp_status", "NLP box not used",
                                "Some NLP checks were skipped; the rest of the scan is unaffected.",
                                items=[{"error": e} for e in errors], confidence=1.0, risk="low", weight=1,
                                suggested_actions=["continue_review"],
                                evidence={"box": str(opts.get("nlp_box") or os.environ.get("NLP_BOX") or DEFAULT_BOX)}))
    return findings
