"""Master Equation Log (.meqlog) — transition ledger for file intelligence.

POF 2828 | 2026-06-19

Tracks every file event: create, move, rename, delete, classify, reclassify.
Each event is one JSON Line. The .meqlog extension is:
  - Plain text (any editor opens it)
  - Markdown-friendly (renders as code blocks)
  - Unique (nothing else uses this extension)
  - Append-only (never overwrite, never truncate)

Per-folder: _chi.meqlog
Master:     ~/.fis/master.meqlog
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

MEQLOG_EXT = ".meqlog"
FOLDER_LOG = "_chi" + MEQLOG_EXT
MASTER_DIR = Path.home() / ".fis"
MASTER_LOG = MASTER_DIR / ("master" + MEQLOG_EXT)

EventType = Literal[
    "create", "move", "rename", "delete", "classify",
    "reclassify", "route", "repair", "archive", "restore",
]

BANNER = (
    "# Master Equation Log (.meqlog) — POF 2828 transition ledger\n"
    "# DO NOT DELETE. Each line is one JSON event. Append-only.\n"
    "# Extension: .meqlog — excluded from all sorting/organizing.\n"
)


# Files we never log events for
IGNORE_SUFFIXES = {MEQLOG_EXT, ".tmp", ".crdownload", ".partial", ".part"}
IGNORE_NAMES = {"thumbs.db", "desktop.ini", ".ds_store", ".fis_meta.json"}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _event_id() -> str:
    return uuid.uuid4().hex[:12]


def _should_ignore(name: str) -> bool:
    low = name.lower()
    if low in IGNORE_NAMES:
        return True
    return any(low.endswith(s) for s in IGNORE_SUFFIXES)


def make_event(
    event_type: EventType,
    path: str,
    chi: float | None = None,
    vector: str | None = None,
    verdict: str | None = None,
    route: str | None = None,
    primary_channel: str | None = None,
    source: str | None = None,
    destination: str | None = None,
    old_name: str | None = None,
    new_name: str | None = None,
    reason: str = "",
    actor: str = "fis",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single .meqlog event dict."""
    event = {
        "id": _event_id(),
        "ts": _now(),
        "type": event_type,
        "path": str(path),
        "actor": actor,
    }
    if chi is not None:
        event["chi"] = round(chi, 8)
    if vector:
        event["vec"] = vector
    if verdict:
        event["verdict"] = verdict
    if route:
        event["route"] = route
    if primary_channel:
        event["primary"] = primary_channel
    if source:
        event["src"] = str(source)
    if destination:
        event["dst"] = str(destination)
    if old_name:
        event["old"] = old_name
    if new_name:
        event["new"] = new_name
    if reason:
        event["reason"] = reason
    if extra:
        event["extra"] = extra
    return event


def _ensure_banner(log_path: Path) -> None:
    """Write the banner header if the file is new or empty."""
    if not log_path.exists() or log_path.stat().st_size == 0:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(BANNER, encoding="utf-8")


def append_event(event: dict[str, Any], folder: str | None = None) -> None:
    """Append one event to the per-folder log and the master log."""
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

    # Per-folder log
    if folder:
        folder_log = Path(folder) / FOLDER_LOG
        try:
            _ensure_banner(folder_log)
            with open(folder_log, "a", encoding="utf-8") as f:
                f.write(line)
        except (OSError, PermissionError):
            pass  # network drives may block writes

    # Master log
    try:
        _ensure_banner(MASTER_LOG)
        with open(MASTER_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except (OSError, PermissionError):
        pass


# ── Convenience loggers ──────────────────────────────────────────────────────

def log_classify(path: str, chi: float, vector: str, verdict: str,
                 route: str, primary: str, folder: str | None = None) -> None:
    if _should_ignore(Path(path).name):
        return
    ev = make_event("classify", path, chi=chi, vector=vector,
                    verdict=verdict, route=route, primary_channel=primary)
    append_event(ev, folder or str(Path(path).parent))


def log_move(source: str, destination: str, reason: str = "",
             chi: float | None = None, vector: str | None = None) -> None:
    if _should_ignore(Path(source).name):
        return
    ev = make_event("move", source, chi=chi, vector=vector,
                    source=source, destination=destination, reason=reason)
    append_event(ev, str(Path(source).parent))
    # Also log at destination
    append_event(ev, str(Path(destination).parent))


def log_rename(folder: str, old_name: str, new_name: str,
               reason: str = "", chi: float | None = None) -> None:
    if _should_ignore(old_name):
        return
    ev = make_event("rename", str(Path(folder) / new_name), chi=chi,
                    old_name=old_name, new_name=new_name, reason=reason)
    append_event(ev, folder)


def log_delete(path: str, reason: str = "",
               chi: float | None = None) -> None:
    if _should_ignore(Path(path).name):
        return
    ev = make_event("delete", path, chi=chi, reason=reason)
    append_event(ev, str(Path(path).parent))


def log_route(path: str, route: str, chi: float, vector: str,
              verdict: str, destination: str, reason: str = "") -> None:
    if _should_ignore(Path(path).name):
        return
    ev = make_event("route", path, chi=chi, vector=vector,
                    verdict=verdict, route=route,
                    destination=destination, reason=reason)
    append_event(ev, str(Path(path).parent))


# ── Log reader ───────────────────────────────────────────────────────────────

def read_log(log_path: str | Path, last_n: int = 50) -> list[dict]:
    """Read the last N events from a .meqlog file."""
    path = Path(log_path)
    if not path.exists():
        return []
    events = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except (OSError, PermissionError):
        return []
    return events[-last_n:]


def read_master_log(last_n: int = 100) -> list[dict]:
    """Read the last N events from the master .meqlog."""
    return read_log(MASTER_LOG, last_n)


def read_folder_log(folder: str, last_n: int = 50) -> list[dict]:
    """Read the last N events from a folder's _chi.meqlog."""
    return read_log(Path(folder) / FOLDER_LOG, last_n)


def stats(log_path: str | Path | None = None) -> dict[str, Any]:
    """Summary statistics from a .meqlog file."""
    events = read_log(log_path or MASTER_LOG, last_n=10000)
    if not events:
        return {"total": 0}
    from collections import Counter
    types = Counter(e.get("type", "?") for e in events)
    routes = Counter(e.get("route", "?") for e in events if e.get("route"))
    verdicts = Counter(e.get("verdict", "?") for e in events if e.get("verdict"))
    chis = [e["chi"] for e in events if "chi" in e]
    return {
        "total": len(events),
        "by_type": dict(types),
        "by_route": dict(routes),
        "by_verdict": dict(verdicts),
        "avg_chi": round(sum(chis) / len(chis), 6) if chis else None,
        "first": events[0].get("ts") if events else None,
        "last": events[-1].get("ts") if events else None,
    }
