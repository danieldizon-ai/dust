"""Structured findings: Dust's verdict as a stable, explainable record for other systems.

`Layer.check` returns everything the checker computed. Integrations (a ministry platform's
conversation evaluator, a draft-review step before a responder sees an AI suggestion, a
moderation queue) need something narrower and stable: what rule was hit, the evidence,
how confident the checker is, and whether a person should look at it. This module turns
a `Verdict` into that record. It adds no judgement of its own.

Finding kinds
-------------
doctrinal_contradiction   asserts something the Creed of 381 (or a loaded extension) excludes
creed_silence             says the Creed leaves open a point it in fact decides
latitude_overclaim        says the Creed settles a question it leaves open (e.g. baptism)
scripture_reference       cites a book, chapter or verse that does not exist
scripture_quote           a quotation does not match the cited verse (needs a Bible text)
obfuscation               look-alike or invisible characters were removed before checking

Notes (not findings)
--------------------
latitude                  the text takes a side on a question the Creed leaves open. This is
                          a legitimate denominational difference, never an error, and is
                          reported so a reviewer can see Dust deliberately did not object.

Review policy
-------------
`review.required` is True for every block (a person should see it before anything is
said to a seeker), for every neural-only finding (no proof), for findings outside the
languages the guard was validated in, and for every Scripture problem. Dust never
recommends acting on a finding without a person.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .layer import Layer, Verdict, Violation

SCHEMA_VERSION = "dust.findings/0.1"

_KIND_BY_SOURCE = {
    "symbolic": "doctrinal_contradiction",
    "neural": "doctrinal_contradiction",
    "creed-claim": "latitude_overclaim",
    "creed-silence": "creed_silence",
}


@dataclass
class Finding:
    rule_id: str                       # P05, L03, C01, REF, QUOTE, OBF
    kind: str
    outcome: str                       # "block" | "flag"
    confidence: float
    method: str                        # symbolic | neural | pattern | scripture | sanitizer
    evidence: dict
    explanation: str
    excluded_errors: list[dict] = field(default_factory=list)
    review: dict = field(default_factory=dict)


@dataclass
class Note:
    rule_id: str
    kind: str
    topic: str
    sentence: str
    explanation: str


@dataclass
class Evaluation:
    schema: str
    decision: str                      # pass | flag | block
    review_required: bool
    findings: list[Finding]
    notes: list[Note]
    boundary: dict
    language: str
    latency_ms: float
    id: str | None = None
    role: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _review(v: Violation, outcome: str, lang: str) -> dict:
    reasons = []
    if outcome == "block":
        reasons.append("blocked content should be seen by a person before anything reaches a seeker")
    if v.source == "neural":
        reasons.append("neural guard only: no symbolic proof")
    if lang not in Layer.BLOCKING_LANGS:
        reasons.append(f"language '{lang}' is outside the guard's validated languages")
    if v.confidence < 0.9 and v.source != "symbolic":
        reasons.append(f"confidence {v.confidence:.2f}")
    return {"required": bool(reasons), "reasons": reasons}


def _explain(layer: Layer, v: Violation) -> str:
    kb = layer.kb
    if v.source == "creed-claim":
        topic = next((t["topic"] for t in kb.latitude if t["id"] == v.proposition), v.proposition)
        return f"Says the Creed of 381 settles '{topic}'. It does not; Christians who confess it differ here."
    try:
        p = kb.proposition(v.proposition)
    except (KeyError, StopIteration, ValueError):
        return v.proof[-1] if v.proof else v.proposition
    if v.source == "creed-silence":
        return f"Treats as open a point the Creed decides: {p.text}"
    return f"Contradicts {p.id}: {p.text}"


def _latitude_notes(layer: Layer, text: str, flagged: set[str]) -> list[Note]:
    notes = []
    sentences = [s for s in re.split(r"(?<=[.!?;])\s+|\n+", text) if s.strip()]
    for t in layer.kb.latitude:
        lid = t.get("id", "")
        cue = Layer._LATITUDE_CUES.get(lid)
        if not cue or lid in flagged:
            continue
        rx = re.compile(r"\b(?:" + cue + r")", re.I)
        for s in sentences:
            if rx.search(s):
                notes.append(Note(lid, "latitude", t["topic"], s.strip(),
                                  "A position on a question the Creed leaves open: a legitimate "
                                  "denominational difference, not a doctrinal error."))
                break
    return notes


def evaluate(layer: Layer, text: str, *, item_id: str | None = None, role: str | None = None,
             include_notes: bool = True) -> Evaluation:
    from .audit import fingerprint

    verdict: Verdict = layer.check(text)
    lang = verdict.sentences[0]["lang"] if verdict.sentences else "unknown"
    findings: list[Finding] = []
    errors_by_id = {e.id: e for e in layer.kb.errors}
    for outcome, group in (("block", verdict.violations), ("flag", verdict.flags)):
        for v in group:
            excluded = [{"id": e, "name": errors_by_id[e].name, "condemned": errors_by_id[e].condemned}
                        for e in v.errors if e in errors_by_id]
            findings.append(Finding(
                rule_id=v.proposition,
                kind=_KIND_BY_SOURCE.get(v.source, "doctrinal_contradiction"),
                outcome=outcome,
                confidence=round(float(v.confidence), 4),
                method="pattern" if v.source in ("creed-claim", "creed-silence") else v.source,
                evidence={"sentence": v.sentence, "proof": list(v.proof)},
                explanation=_explain(layer, v),
                excluded_errors=excluded,
                review=_review(v, outcome, lang),
            ))
    for r in verdict.references:
        if not r["exists"]:
            findings.append(Finding("REF", "scripture_reference", "flag", 1.0, "scripture",
                                    {"reference": r["canonical"], "problem": r["problem"]},
                                    f"{r['canonical']} does not exist: {r['problem']}.",
                                    review={"required": True, "reasons": ["invalid Scripture reference"]}))
        elif r.get("quote_similarity") is not None and r["quote_similarity"] < layer.min_quote_similarity:
            findings.append(Finding("QUOTE", "scripture_quote", "flag", round(1 - r["quote_similarity"], 4),
                                    "scripture",
                                    {"reference": r["canonical"], "quote": r.get("quote"),
                                     "similarity": r["quote_similarity"]},
                                    f"The quotation does not match {r['canonical']}.",
                                    review={"required": True, "reasons": ["possible misquotation"]}))
    if verdict.obfuscated:
        findings.append(Finding("OBF", "obfuscation", "flag", 1.0, "sanitizer", {},
                                "Look-alike or invisible characters were removed before checking.",
                                review={"required": True, "reasons": ["input looked engineered to evade checks"]}))
    flagged_lat = {f.rule_id for f in findings if f.kind == "latitude_overclaim"}
    notes = _latitude_notes(layer, text, flagged_lat) if include_notes else []
    return Evaluation(
        schema=SCHEMA_VERSION,
        decision=verdict.decision,
        review_required=any(f.review.get("required") for f in findings),
        findings=findings,
        notes=notes,
        boundary={"fingerprint": fingerprint(layer.kb), "extensions": sorted(layer.kb.extensions),
                  "version": layer.kb.version},
        language=lang,
        latency_ms=round(verdict.latency_ms, 2),
        id=item_id,
        role=role,
    )
