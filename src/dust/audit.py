"""Audit the encoded boundary itself.

The checker is only as good as the knowledge base it checks against. ``audit`` tests
properties the encoding must have, independent of any model or benchmark:

* **consistency**: the Creed's own literals, closed under the inference rules, never
  derive a literal together with its negation (the boundary does not contradict itself);
* **every excluded error is excluded**: each error's signature literals, closed under the
  rules, contradict at least one of the propositions the error is recorded as denying;
* **grounding**: every proposition has a Greek anchor and at least one Scripture
  reference, and every reference exists in the versification table;
* **reach**: core propositions that no recorded error touches are listed, so reviewers
  can see which articles are only protected by patterns;
* **fingerprint**: a SHA-256 over the canonical knowledge base, so a deployment can state
  exactly which boundary it enforces and a fork that changes it is visible.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .kb import KnowledgeBase, load, negate
from . import scripture


def closure(literals, kb: KnowledgeBase) -> set[str]:
    index: dict[str, list[str]] = {}
    for r in kb.rules:
        index.setdefault(r.premise, []).extend(r.conclusions)
    seen: set[str] = set()
    todo = list(literals)
    while todo:
        lit = todo.pop()
        if lit in seen:
            continue
        seen.add(lit)
        todo.extend(index.get(lit, []))
    return seen


def fingerprint(kb: KnowledgeBase) -> str:
    canon = {
        "propositions": [[p.id, p.severity, sorted(p.literals)] for p in sorted(kb.propositions, key=lambda p: p.id)],
        "errors": [[e.id, sorted(e.contradicts)] for e in sorted(kb.errors, key=lambda e: e.id)],
        "rules": sorted([r.id, r.premise, sorted(r.conclusions)] for r in kb.rules),
        "signatures": {k: sorted(v) for k, v in sorted(kb.error_signatures.items())},
        "latitude": sorted(t.get("id", "") for t in kb.latitude),
        "extensions": sorted(kb.extensions),
    }
    blob = json.dumps(canon, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


@dataclass
class AuditReport:
    fingerprint: str
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.problems

    def to_dict(self) -> dict:
        return {"ok": self.ok, "fingerprint": self.fingerprint, "problems": self.problems,
                "warnings": self.warnings, "stats": self.stats}


def audit(kb: KnowledgeBase | None = None) -> AuditReport:
    kb = kb or load()
    rep = AuditReport(fingerprint(kb))
    axioms = set(kb.axioms)

    # 1. consistency of the boundary with itself
    closed = closure(axioms, kb)
    clashes = sorted(l for l in closed if not l.startswith("-") and negate(l) in closed)
    for l in clashes:
        rep.problems.append(f"inconsistent: the Creed's literals derive both {l} and -{l}")

    # 2. each excluded error is actually excluded, by the propositions it is said to deny
    touched: set[str] = set()
    for e in kb.errors:
        sig = kb.error_signatures.get(e.id)
        if not sig:
            rep.problems.append(f"{e.id} ({e.name}) has no signature literals")
            continue
        derived = closure(sig, kb)
        hit = {kb.axioms[negate(l)] for l in derived if negate(l) in kb.axioms}
        touched |= hit
        if not hit:
            rep.problems.append(f"{e.id} ({e.name}) contradicts no proposition after inference")
        elif not hit & set(e.contradicts):
            rep.problems.append(f"{e.id} ({e.name}) is recorded as denying {list(e.contradicts)} "
                                f"but its signature only contradicts {sorted(hit)}")
        missing = [p for p in e.contradicts if p not in {q.id for q in kb.propositions}]
        if missing:
            rep.problems.append(f"{e.id} refers to unknown propositions {missing}")

    # 3. grounding in the text and in Scripture
    bad_refs = 0
    for p in kb.propositions:
        if not p.greek:
            rep.warnings.append(f"{p.id} has no Greek anchor")
        if not p.scripture:
            rep.warnings.append(f"{p.id} has no Scripture reference")
        for ref in p.scripture:
            found = scripture.find(ref)
            if not found or not all(r.exists for r in found):
                bad_refs += 1
                rep.problems.append(f"{p.id} cites a reference that does not exist: {ref}")

    # 4. reach: which core articles no recorded error touches
    core = [p.id for p in kb.propositions if p.severity == "core"]
    untouched = [pid for pid in core if pid not in touched]
    for pid in untouched:
        rep.warnings.append(f"{pid} is not contradicted by any recorded error (protected only by patterns)")

    rep.stats = {"propositions": len(kb.propositions), "core": len(core), "errors": len(kb.errors),
                 "rules": len(kb.rules), "latitude": len(kb.latitude), "closure_size": len(closed),
                 "core_reached_by_errors": len(core) - len(untouched), "bad_references": bad_refs,
                 "extensions": list(kb.extensions)}
    return rep
