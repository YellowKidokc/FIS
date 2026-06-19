"""χ-Evaluator v2 Engine — 10-channel coherence scoring for file intelligence.

POF 2828 | 2026-06-19

Scores files across the Master Equation's ten channels:
  χ = G · M · E · S_eff · T · K · R · Q · F · C

Each channel produces v_pos (coherent) and v_neg (corrupted),
effective_score = v_pos × (1 − v_neg).  Product of all ten = χ.

A zero channel collapses total coherence → file gets flagged.

This engine plugs into the FIS orchestrator via analyze().
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from core.models import Finding


# ── Channel definitions ──────────────────────────────────────────────────────

CHANNELS: dict[str, str] = {
    "G": "External input / dependency honesty",
    "M": "Alignment / reference standard",
    "E": "Truth / signal fidelity",
    "S": "Entropy / disorder cost",
    "T": "Temporal persistence",
    "K": "Compression / wisdom density",
    "R": "Phase transition / regime change",
    "Q": "Free will / invitation vs coercion",
    "F": "Cross-context binding",
    "C": "Integration / whole-system coherence",
}

CHANNEL_ORDER = ["G", "M", "E", "S", "T", "K", "R", "Q", "F", "C"]

Verdict = Literal[
    "coherent", "partially_coherent", "fragile",
    "high_signal_deception", "collapsed", "repairable",
]


def clamp01(x: float) -> float:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return 0.0
    return max(0.0, min(1.0, float(x)))


# ── Channel result ───────────────────────────────────────────────────────────

@dataclass
class ChannelScore:
    channel: str
    name: str
    v_pos: float
    v_neg: float
    effective: float
    gradient: int          # -1, 0, +1
    confidence: float
    reason: str = ""
    failure_mode: str = ""
    repair_path: str = ""

    @classmethod
    def build(cls, ch: str, vp: float, vn: float, grad: int,
              conf: float, reason: str = "",
              fail: str = "", repair: str = "") -> "ChannelScore":
        vp, vn = clamp01(vp), clamp01(vn)
        return cls(
            channel=ch, name=CHANNELS.get(ch, ch),
            v_pos=vp, v_neg=vn,
            effective=round(vp * (1.0 - vn), 6),
            gradient=max(-1, min(1, int(grad))),
            confidence=clamp01(conf),
            reason=reason, failure_mode=fail, repair_path=repair,
        )


# ── Chi evaluation result ────────────────────────────────────────────────────

@dataclass
class ChiResult:
    chi: float
    channels: list[ChannelScore]
    vector: str                     # G1M0E1S0T0K1R0Q0F0C1
    zero_channels: list[str]
    weakest: list[str]
    strongest: list[str]
    verdict: Verdict
    route: str                      # canonical | review | archive | repair | quarantine
    meq_primary: str                # dominant channel code
    meq_secondary: list[str]
    timestamp: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False, default=str)


def chi_product(channels: list[ChannelScore]) -> float:
    result = 1.0
    for c in channels:
        result *= clamp01(c.effective)
    return round(result, 8)


def chi_vector(channels: list[ChannelScore]) -> str:
    return "".join(
        f"{c.channel}{1 if c.effective > 0.10 else 0}"
        for c in channels
    )


def infer_verdict(chi: float, zeros: list[str],
                  channels: list[ChannelScore]) -> Verdict:
    if zeros:
        fatal = {"coercion", "contradiction", "self-sealing", "unfalsifiable"}
        modes = {c.failure_mode.lower().strip() for c in channels
                 if c.channel in zeros and c.failure_mode}
        return "collapsed" if modes & fatal else "repairable"

    ch = {c.channel: c for c in channels}
    if (ch["E"].effective > 0.70 and
        (ch["Q"].effective < 0.25 or ch["K"].effective < 0.25
         or ch["T"].effective < 0.25)):
        return "high_signal_deception"

    if chi > 0.50:
        return "coherent"
    if chi >= 0.10:
        return "partially_coherent"
    if chi >= 0.01:
        return "fragile"
    return "collapsed"


def infer_route(verdict: Verdict, chi: float) -> str:
    return {
        "coherent": "canonical",
        "partially_coherent": "review",
        "fragile": "archive",
        "high_signal_deception": "quarantine",
        "collapsed": "archive",
        "repairable": "repair",
    }.get(verdict, "review")



# ── Local NLP scoring (uses port 8700 when available) ────────────────────────

NLP_API = "http://localhost:8700/nlp"

def _nlp_call(endpoint: str, payload: dict, timeout: float = 30) -> dict:
    """Call the shared NLP FastAPI. Returns empty dict on failure."""
    try:
        import urllib.request
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{NLP_API}/{endpoint}", data=data, method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return {}


def _word_count(text: str) -> int:
    return len(text.split())


def _has_equations(text: str) -> bool:
    return bool(re.search(r"\\[({]|\\frac|\\int|\$\$|R\^2|e\^{", text))


def _has_citations(text: str) -> bool:
    return bool(re.search(r"\[\d+\]|\bcf\.\b|\bsee\b.*\[\[", text, re.I))


def _has_data_tables(text: str) -> bool:
    return text.count("|") > 10


def _signal_density(text: str) -> float:
    """Ratio of non-whitespace, non-markup content to total length."""
    stripped = re.sub(r"[#*_\-|`>\[\](){}\\]", "", text)
    stripped = re.sub(r"\s+", " ", stripped).strip()
    return min(1.0, len(stripped) / max(len(text), 1))


def score_file_channels(text: str, filename: str = "",
                        metadata: dict | None = None) -> list[ChannelScore]:
    """Score a file's content across 10 channels using local heuristics + NLP API.

    This is the LIGHTWEIGHT pass — no LLM calls. Uses:
    - Text statistics (word count, density, equations, citations)
    - NLP API (summarize, NER, classify) when available
    - Structural signals (frontmatter, headings, cross-refs)
    """
    meta = metadata or {}
    wc = _word_count(text)
    has_eq = _has_equations(text)
    has_cite = _has_citations(text)
    has_tables = _has_data_tables(text)
    density = _signal_density(text)
    has_frontmatter = text.lstrip().startswith("---")
    heading_count = len(re.findall(r"^#{1,6}\s", text, re.M))
    crossref_count = len(re.findall(r"\[\[.+?\]\]", text))

    # Try NLP API for richer signals
    nlp_summary = _nlp_call("summarize", {"text": text[:4000]})
    nlp_ner = _nlp_call("ner", {"text": text[:3000]})
    entity_count = len(nlp_ner.get("entities", nlp_ner.get("data", [])))

    channels: list[ChannelScore] = []

    # G — External input / dependency honesty
    # Does this file declare its sources or hide them?
    g_pos = 0.5
    if has_cite:
        g_pos += 0.3
    if has_frontmatter:
        g_pos += 0.1
    if "source" in text.lower()[:500] or "reference" in text.lower()[:500]:
        g_pos += 0.1
    channels.append(ChannelScore.build("G", clamp01(g_pos), 0.05, 0, 0.7,
        f"citations={has_cite} frontmatter={has_frontmatter}"))

    # M — Alignment / reference standard
    # Does this match known project structure?
    m_pos = 0.4
    if has_frontmatter:
        m_pos += 0.2
    if heading_count >= 3:
        m_pos += 0.15
    if any(k in filename.lower() for k in ["gtq", "mda", "logos", "paper", "law"]):
        m_pos += 0.25
    channels.append(ChannelScore.build("M", clamp01(m_pos), 0.05, 0, 0.65,
        f"headings={heading_count} project_match={m_pos > 0.6}"))

    # E — Truth / signal fidelity
    # Is there real content or is this noise?
    e_pos = min(1.0, density * 0.7 + (0.2 if wc > 200 else 0.0) + (0.1 if has_eq else 0.0))
    e_neg = 0.3 if wc < 50 else 0.1 if wc < 200 else 0.02
    channels.append(ChannelScore.build("E", e_pos, e_neg, 0, 0.8,
        f"words={wc} density={density:.2f} equations={has_eq}",
        fail="no_signal" if wc < 50 else ""))


    # S — Entropy / disorder cost
    # Is this file a duplicate, a fragment, poorly named?
    s_neg = 0.1
    if re.search(r"\(\d+\)\.|copy|duplicate|backup|old|temp", filename, re.I):
        s_neg += 0.4
    if wc < 20:
        s_neg += 0.3  # fragment
    s_pos = 0.7 if s_neg < 0.3 else 0.3
    channels.append(ChannelScore.build("S", s_pos, clamp01(s_neg),
        -1 if s_neg > 0.4 else 0, 0.75,
        f"dup_signals={s_neg > 0.3} fragment={wc < 20}",
        fail="entropy" if s_neg > 0.5 else ""))

    # T — Temporal persistence
    # Is this file still relevant or superseded?
    t_pos = 0.6
    if meta.get("age_days", 0) > 365:
        t_pos -= 0.2
    if "deprecated" in text.lower()[:1000] or "superseded" in text.lower()[:1000]:
        t_pos -= 0.3
    if "canonical" in text.lower()[:1000] or "final" in filename.lower():
        t_pos += 0.2
    channels.append(ChannelScore.build("T", clamp01(t_pos), 0.05, 0, 0.6,
        f"age={meta.get('age_days', '?')}d"))

    # K — Compression / wisdom density
    # How much information per byte?
    k_pos = density * 0.5 + (0.15 if has_eq else 0) + (0.15 if has_tables else 0)
    k_pos += min(0.2, heading_count * 0.03)  # structured = compressible
    if nlp_summary.get("summary"):
        k_pos += 0.1  # summarizable = compressible
    channels.append(ChannelScore.build("K", clamp01(k_pos), 0.05, 0, 0.7,
        f"density={density:.2f} tables={has_tables} eq={has_eq}"))

    # R — Phase transition / regime change
    # Is this a version migration, deprecated format?
    r_neg = 0.0
    if any(x in filename.lower() for x in ["_v1", "_v2", "_old", "_new", "migration"]):
        r_neg += 0.3
    r_pos = 0.6 if r_neg < 0.2 else 0.4
    channels.append(ChannelScore.build("R", r_pos, clamp01(r_neg), 0, 0.5,
        f"version_signals={r_neg > 0.1}"))

    # Q — Free will / invitation vs coercion
    # Files always score high here (files don't coerce).
    # Low Q only if file contains manipulative patterns.
    q_neg = 0.0
    urgency_words = len(re.findall(r"\b(urgent|immediately|act now|limited time)\b",
                                    text[:2000], re.I))
    if urgency_words > 2:
        q_neg += 0.3
    channels.append(ChannelScore.build("Q", 0.85, clamp01(q_neg), 0, 0.9,
        f"urgency_words={urgency_words}",
        fail="coercion" if q_neg > 0.3 else ""))

    # F — Cross-context binding
    # Does this file connect to other files?
    f_pos = 0.3
    f_pos += min(0.4, crossref_count * 0.05)
    if entity_count > 5:
        f_pos += 0.15
    if any(k in text.lower() for k in ["master equation", "chi", "law "]):
        f_pos += 0.15
    channels.append(ChannelScore.build("F", clamp01(f_pos), 0.05, 0, 0.65,
        f"crossrefs={crossref_count} entities={entity_count}"))

    # C — Integration / whole-system coherence
    # Does this file fit the overall system?
    c_pos = 0.4
    if has_frontmatter and heading_count >= 2 and wc > 300:
        c_pos += 0.3  # well-structured
    if crossref_count > 0:
        c_pos += 0.15  # connected
    if has_eq and has_cite:
        c_pos += 0.15  # rigorous
    channels.append(ChannelScore.build("C", clamp01(c_pos), 0.05, 0, 0.7,
        f"structured={c_pos > 0.6}"))

    return channels


# ── Evaluate a single file ───────────────────────────────────────────────────

def evaluate_file(file_path: str, text: str | None = None,
                  metadata: dict | None = None) -> ChiResult:
    """Run full χ evaluation on a file. Returns ChiResult."""
    path = Path(file_path)
    if text is None:
        try:
            text = path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            text = ""

    channels = score_file_channels(text, path.name, metadata)
    chi = chi_product(channels)
    vec = chi_vector(channels)
    zeros = [c.channel for c in channels if c.effective <= 0.001]
    sorted_ch = sorted(channels, key=lambda c: c.effective)
    weakest = [c.channel for c in sorted_ch[:3]]
    strongest = [c.channel for c in sorted_ch[-3:]][::-1]
    verdict = infer_verdict(chi, zeros, channels)
    route = infer_route(verdict, chi)

    # Primary = highest scoring channel, secondary = next two
    primary = strongest[0] if strongest else "C"
    secondary = strongest[1:3] if len(strongest) > 1 else []

    return ChiResult(
        chi=chi, channels=channels, vector=vec,
        zero_channels=zeros, weakest=weakest, strongest=strongest,
        verdict=verdict, route=route,
        meq_primary=primary, meq_secondary=secondary,
        timestamp=datetime.now().isoformat(),
    )


# ── FIS engine interface ─────────────────────────────────────────────────────

def analyze(folderbrain, cache=None, options=None) -> list[Finding]:
    """FIS orchestrator entry point. Scores files in the folder by χ."""
    findings: list[Finding] = []
    files = folderbrain.inventory.get("files", [])

    scored = []
    for f in files[:200]:  # cap for performance
        fpath = f.get("path") or f.get("name", "")
        if not fpath:
            continue
        full = Path(folderbrain.folder_path) / fpath
        if not full.exists() or full.stat().st_size == 0:
            continue
        if full.suffix.lower() not in {".md", ".txt", ".html", ".json", ".py"}:
            continue  # only score text files

        try:
            result = evaluate_file(str(full))
            scored.append({
                "file": f.get("name", fpath),
                "chi": result.chi,
                "vector": result.vector,
                "verdict": result.verdict,
                "route": result.route,
                "primary": result.meq_primary,
                "zeros": result.zero_channels,
                "weakest": result.weakest,
            })
        except Exception:
            continue

    if not scored:
        return findings

    # Summary finding
    canonical = [s for s in scored if s["route"] == "canonical"]
    repair = [s for s in scored if s["route"] == "repair"]
    archive = [s for s in scored if s["route"] == "archive"]
    quarantine = [s for s in scored if s["route"] == "quarantine"]
    avg_chi = sum(s["chi"] for s in scored) / len(scored)

    findings.append(Finding(
        finding_id="chi_eval_001",
        engine="chi_evaluator",
        finding_type="coherence_scan",
        title=f"χ Coherence Scan — {len(scored)} files scored",
        summary=(
            f"Average χ={avg_chi:.4f}. "
            f"{len(canonical)} canonical, {len(repair)} repairable, "
            f"{len(archive)} archive, {len(quarantine)} quarantined."
        ),
        items=scored,
        confidence=0.75,
        risk="medium" if repair or quarantine else "low",
        weight=8,
        suggested_actions=[
            "route_by_chi", "review_zero_channels",
            "repair_repairable", "archive_low_chi",
        ],
        evidence={
            "avg_chi": avg_chi,
            "total_scored": len(scored),
            "route_counts": {
                "canonical": len(canonical),
                "review": len([s for s in scored if s["route"] == "review"]),
                "repair": len(repair),
                "archive": len(archive),
                "quarantine": len(quarantine),
            },
        },
    ))

    # Zero-channel finding (most actionable)
    zero_files = [s for s in scored if s["zeros"]]
    if zero_files:
        findings.append(Finding(
            finding_id="chi_zeros_001",
            engine="chi_evaluator",
            finding_type="zero_channel",
            title=f"Zero-channel collapse — {len(zero_files)} files",
            summary="These files have at least one χ channel at zero, collapsing total coherence.",
            items=zero_files,
            confidence=0.9,
            risk="high",
            weight=9,
            suggested_actions=["inspect_zeros", "repair_or_archive"],
            evidence={"zero_files": len(zero_files)},
        ))

    return findings
