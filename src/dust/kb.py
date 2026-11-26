"""The doctrinal knowledge base: the Creed of 381 as propositions, the errors it
excludes, the latitude it leaves, inference rules and Scripture references."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources


def _load(name: str) -> dict:
    return json.loads(resources.files("dust.data").joinpath(name).read_text(encoding="utf-8"))


def negate(literal: str) -> str:
    return literal[1:] if literal.startswith("-") else "-" + literal


@dataclass(frozen=True)
class Proposition:
    id: str
    group: str
    severity: str  # "core" blocks, "ecclesial" annotates
    text: str
    greek: str
    literals: tuple[str, ...]
    scripture: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class ExcludedError:
    id: str
    name: str
    summary: str
    contradicts: tuple[str, ...]
    condemned: str


@dataclass(frozen=True)
class Rule:
    id: str
    premise: str
    conclusions: tuple[str, ...]
    why: str


@dataclass(eq=False)
class KnowledgeBase:
    title: str
    version: str
    attribution: str
    texts: dict
    propositions: list[Proposition]
    errors: list[ExcludedError]
    latitude: list[dict]
    rules: list[Rule]
    error_signatures: dict[str, list[str]]
    scripture: dict[str, str]
    axioms: dict[str, str] = field(default_factory=dict)  # literal -> proposition id
    extensions: list[str] = field(default_factory=list)
    extra_patterns: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        for p in self.propositions:
            for lit in p.literals:
                self.axioms[lit] = p.id

    def proposition(self, pid: str) -> Proposition:
        return next(p for p in self.propositions if p.id == pid)

    def error(self, eid: str) -> ExcludedError:
        return next(e for e in self.errors if e.id == eid)

    def errors_for(self, literals: set[str]) -> list[ExcludedError]:
        return [self.error(eid) for eid, sig in self.error_signatures.items() if literals & set(sig)]

    def creed_text(self, lang: str = "en") -> str:
        return self.texts[lang]["text"]

    def verses(self, pid: str) -> list[tuple[str, str]]:
        return [(ref, self.scripture[ref]) for ref in self.proposition(pid).scripture if ref in self.scripture]

    def __hash__(self) -> int:  # identity hash so a KnowledgeBase can key caches
        return id(self)


def load(extensions: tuple[str, ...] | list[str] = ()) -> KnowledgeBase:
    """The Nicene knowledge base, optionally with confession extensions stacked on top.

    An extension is the name of a bundled file in dust/data/extensions/ (for example
    "chalcedon-451") or a path to a JSON file with the same shape: propositions,
    excluded_errors, rules, error_signatures and patterns. Extensions can only add
    to the boundary; they cannot remove Nicene propositions.
    """
    base = _load_base()
    if not extensions:
        return base
    return _with_extensions(base, tuple(extensions))


@lru_cache(maxsize=8)
def _with_extensions(base: "KnowledgeBase", names: tuple[str, ...]) -> "KnowledgeBase":
    import copy
    from pathlib import Path
    kb = copy.deepcopy(base)
    for name in names:
        if name.endswith(".json"):
            ext = json.loads(Path(name).read_text(encoding="utf-8"))
        else:
            ext = json.loads(resources.files("dust.data").joinpath("extensions", f"{name}.json").read_text(encoding="utf-8"))
        ids = {p.id for p in kb.propositions}
        for p in ext.get("propositions", []):
            if p["id"] in ids:
                raise ValueError(f"extension {ext['id']} redefines proposition {p['id']}")
            prop = Proposition(p["id"], p["group"], p["severity"], p["text"], p.get("greek", ""),
                               tuple(p["literals"]), tuple(p.get("scripture", [])), p.get("note", ""))
            kb.propositions.append(prop)
            for lit in prop.literals:
                kb.axioms[lit] = prop.id
        for e in ext.get("excluded_errors", []):
            kb.errors.append(ExcludedError(e["id"], e["name"], e["summary"], tuple(e["contradicts"]), e["condemned"]))
        for r in ext.get("rules", []):
            kb.rules.append(Rule(r["id"], r["if"], tuple(r["then"]), r["why"]))
        kb.error_signatures.update(ext.get("error_signatures", {}))
        kb.extra_patterns.extend(ext.get("patterns", []))
        kb.latitude.extend(ext.get("latitude", []))
        kb.extensions.append(ext["id"])
    return kb


@lru_cache(maxsize=1)
def _load_base() -> KnowledgeBase:
    creed = _load("creed.json")
    rules = _load("rules.json")
    scripture = _load("scripture.json")
    return KnowledgeBase(
        title=creed["title"],
        version=creed["version"],
        attribution=creed["attribution"],
        texts=creed["texts"],
        propositions=[
            Proposition(p["id"], p["group"], p["severity"], p["text"], p["greek"],
                        tuple(p["literals"]), tuple(p["scripture"]), p.get("note", ""))
            for p in creed["propositions"]
        ],
        errors=[
            ExcludedError(e["id"], e["name"], e["summary"], tuple(e["contradicts"]), e["condemned"])
            for e in creed["excluded_errors"]
        ],
        latitude=creed["latitude"],
        rules=[Rule(r["id"], r["if"], tuple(r["then"]), r["why"]) for r in rules["rules"]],
        error_signatures=rules["error_signatures"],
        scripture=scripture["verses"],
    )
