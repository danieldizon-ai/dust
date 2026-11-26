"""The alignment layer: dual-track checking, the Nicene constitution, retrieval of the
relevant articles and Scripture, and a generate-check-repair loop around any model."""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field
from importlib import resources
from typing import Callable, Protocol

from . import harden, scripture, symbolic
from .kb import KnowledgeBase, load
from .neural import Guard
from .langid import detect

Message = dict  # {"role": "system"|"user"|"assistant", "content": str}


@dataclass
class Violation:
    proposition: str
    source: str                  # "symbolic" | "neural"
    confidence: float
    sentence: str
    errors: list[str] = field(default_factory=list)
    proof: list[str] = field(default_factory=list)
    severity: str = "core"


@dataclass
class Verdict:
    decision: str                # "pass" | "flag" | "block"
    violations: list[Violation]
    flags: list[Violation]
    affirmed: list[str]
    sentences: list[dict]
    latency_ms: float
    references: list[dict] = field(default_factory=list)
    obfuscated: bool = False     # input carried invisible or look-alike characters (removed before checking)

    @property
    def invalid_references(self) -> list[dict]:
        return [r for r in self.references if not r["exists"]]

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def ok(self) -> bool:
        return self.decision != "block"


class Backend(Protocol):
    def generate(self, messages: list[Message], **kw) -> str: ...


_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
_ANCHOR = re.compile(r"\b(?:SON|FATHER|SPIRIT|GOD|TRINITY|gods?|divine|divinity|deity|resurrection|resurrected|risen|tomb|virgin|creed|heaven|hell|death|dead|die|died|cross|crucif\w*|incarnat\w*|creat\w*|creature|prophet|messiah|kingdom|judge\w*|baptis\w*|church|eucharist|salvation|sin|sins|soul|angel|world|universe|matter|myth|metaphor|persons?|modes?)\b|[^\x00-\x7f]", re.I)


class Layer:
    """Nicene (381) alignment layer.

    mode:
      "dual"      symbolic proof blocks; neural blocks only where the symbolic track has
                  no claim and the sentence is an assertion (default)
      "symbolic"  symbolic track only
      "neural"    neural track only
    """

    # Languages in which the neural guard was trained and evaluated, so it may block.
    # Elsewhere it can only flag; use `translate` to pivot through English instead.
    BLOCKING_LANGS = frozenset({"en", "es", "pt"})

    def __init__(self, kb: KnowledgeBase | None = None, guard: Guard | None = None, mode: str = "dual",
                 block_threshold: float | None = None, flag_threshold: float | None = None,
                 translate: Callable[[str], str] | None = None, extensions: tuple[str, ...] | list[str] = (),
                 bible=None, min_quote_similarity: float = 0.85,
                 stance_gate: bool = True, restrict_languages: bool = True, sanitize: bool = True):
        self.sanitize = sanitize
        self.kb = kb or load(tuple(extensions))
        self.bible = bible
        self.stance_gate = stance_gate
        self.restrict_languages = restrict_languages
        self.min_quote_similarity = min_quote_similarity
        self.guard = guard if guard is not None or mode == "symbolic" else Guard.load()
        self.mode = mode
        self.translate = translate
        meta = self.guard.meta if self.guard else {}
        self.block_threshold = block_threshold if block_threshold is not None else meta.get("threshold_block", 0.5)
        self.flag_threshold = flag_threshold if flag_threshold is not None else meta.get("threshold_flag", 0.35)

    # ------------------------------------------------------------------ checking
    def check(self, text: str) -> Verdict:
        t0 = time.perf_counter()
        obfuscated = False
        if self.sanitize:
            cleaned = harden.sanitize(text)
            obfuscated = harden.was_obfuscated(text, cleaned)
            text = cleaned
        lang = detect(text)
        if self.translate is not None and lang not in ("en", "unknown"):
            text = self.translate(text)
            lang = "en"
        raw_sents = [s for s in _SPLIT.split(text) if s and s.strip()]
        violations: list[Violation] = []
        flags: list[Violation] = []
        affirmed: set[str] = set()
        report: list[dict] = []
        sym_claims = symbolic.extract(text, self.kb.extra_patterns) if self.mode != "neural" else []
        for i, raw in enumerate(raw_sents):
            claims = [c for c in sym_claims if c.sentence_index == i]
            res = symbolic.infer(claims, self.kb) if claims else symbolic.SymbolicResult()
            norm = symbolic.normalise(raw)
            st = symbolic.stance(norm[0], raw) if norm else "assert"
            row = {"text": raw, "stance": st, "lang": lang, "claims": [c.literal for c in claims]}
            affirmed.update(res.affirmed)
            for c in res.contradictions:
                p = self.kb.proposition(c.proposition)
                v = Violation(c.proposition, "symbolic", 1.0, raw, res.errors, c.proof, p.severity)
                (violations if p.severity == "core" else flags).append(v)
            if self.guard is not None and self.mode != "symbolic":
                s = self.guard.scores(raw)
                row["p_contradicts"] = round(s["contradicts"], 4)
                asserted_claims = [c for c in claims if c.asserted]
                # Neural checking needs doctrinal content in the sentence itself: a
                # fragment like "it happened." carries none and the guard is unreliable on it.
                anchored = bool(_ANCHOR.search(" ".join(norm)))
                if self.mode == "neural":
                    gate_open = anchored
                elif self.stance_gate:
                    gate_open = anchored and st == "assert" and not asserted_claims and not res.contradictions
                else:  # ablation: neural may block wherever the symbolic track found no contradiction
                    gate_open = not res.contradictions
                if gate_open and s["contradicts"] >= self.flag_threshold:
                    group, _ = self.guard.group(raw)
                    pid = self._group_to_prop(group)
                    v = Violation(pid, "neural", s["contradicts"], raw, [], [f"guard p(contradicts)={s['contradicts']:.2f}, group={group}"])
                    can_block = s["contradicts"] >= self.block_threshold and (lang in self.BLOCKING_LANGS or not self.restrict_languages)
                    (violations if can_block else flags).append(v)
            report.append(row)
        refs = scripture.find(text)
        if self.bible is not None:
            scripture.check_quotes(text, self.bible, refs)
        ref_problems = [r for r in refs if not r.exists or (r.quote_similarity is not None and r.quote_similarity < self.min_quote_similarity)]
        decision = "block" if violations else ("flag" if flags or ref_problems else "pass")
        return Verdict(decision, violations, flags, sorted(affirmed), report, (time.perf_counter() - t0) * 1000,
                       [asdict(r) | {"canonical": r.canonical} for r in refs], obfuscated)

    def _group_to_prop(self, group: str) -> str:
        for p in self.kb.propositions:
            if p.group == group:
                return p.id
        return "P01"

    # ------------------------------------------------------------------ prompting
    def constitution(self) -> str:
        return resources.files("dust.data").joinpath("constitution.md").read_text(encoding="utf-8")

    def system_prompt(self, query: str | None = None, lang: str = "en", k: int = 3) -> str:
        parts = [self.constitution().strip(), "", "The Creed (AD 381):", self.kb.creed_text(lang)]
        if query:
            ctx = self.retrieve(query, k)
            if ctx:
                parts += ["", "Articles of the Creed most relevant to this question, with Scripture (World English Bible):"]
                for p in ctx:
                    parts.append(f"- {p.id}: {p.text}")
                    for ref, verse in self.kb.verses(p.id)[:2]:
                        parts.append(f"    {ref}: {verse}")
        return "\n".join(parts)

    def retrieve(self, query: str, k: int = 3):
        """Rank propositions by overlap with the query (BM25-style over proposition text,
        Greek anchor, excluded-error names and Scripture). Small, fast and offline."""
        from .rag import rank
        return rank(self.kb, query, k)

    # ------------------------------------------------------------------ generation
    def wrap(self, backend: Backend | Callable[[list[Message]], str], max_repairs: int = 2) -> "AlignedModel":
        return AlignedModel(self, backend, max_repairs)


@dataclass
class AlignedResponse:
    content: str
    verdict: Verdict
    attempts: int
    repaired: bool
    refused: bool
    drafts: list[str]


class AlignedModel:
    """generate -> check -> (repair with a citation of the article) -> fallback."""

    def __init__(self, layer: Layer, backend, max_repairs: int = 2):
        self.layer = layer
        self.backend = backend
        self.max_repairs = max_repairs

    def _gen(self, messages: list[Message]) -> str:
        if hasattr(self.backend, "generate"):
            return self.backend.generate(messages)
        return self.backend(messages)

    def chat(self, messages: list[Message], ground: bool = True) -> AlignedResponse:
        user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        sys_msg = {"role": "system", "content": self.layer.system_prompt(user if ground else None)}
        convo = [sys_msg] + [m for m in messages if m["role"] != "system"]
        drafts: list[str] = []
        verdict = None
        for attempt in range(self.max_repairs + 1):
            draft = self._gen(convo)
            drafts.append(draft)
            verdict = self.layer.check(draft)
            if verdict.ok:
                return AlignedResponse(draft, verdict, attempt + 1, attempt > 0, False, drafts)
            convo = convo + [{"role": "assistant", "content": draft},
                             {"role": "system", "content": self._repair_note(verdict)}]
        return AlignedResponse(self._fallback(verdict), verdict, len(drafts), False, True, drafts)

    def _repair_note(self, verdict: Verdict) -> str:
        lines = ["Your previous draft states, as your own view, something the Creed of 381 excludes. Rewrite it."]
        for v in verdict.violations:
            p = self.layer.kb.proposition(v.proposition)
            lines.append(f'- "{v.sentence}" conflicts with {p.id}: {p.text}')
        lines.append("You may describe other views as reported views (\"Arius taught that ...\"), "
                     "but do not assert them. Keep everything else that was correct.")
        return "\n".join(lines)

    def _fallback(self, verdict: Verdict) -> str:
        kb = self.layer.kb
        pids = sorted({v.proposition for v in verdict.violations})
        out = ["I can't give that answer as my own view, because it conflicts with the Nicene Creed (381), "
               "the boundary this assistant works within. What the Creed confesses on this point:"]
        for pid in pids:
            p = kb.proposition(pid)
            refs = ", ".join(r for r, _ in kb.verses(pid))
            out.append(f"- {p.text} (see {refs})")
        out.append("I'm happy to explain the history of this question or how different traditions read it.")
        return "\n".join(out)
