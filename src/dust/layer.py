"""The alignment layer: dual-track checking, the Nicene constitution, retrieval of the
relevant articles and Scripture, and a generate-check-repair loop around any model."""
from __future__ import annotations

import re
import time
from dataclasses import asdict, dataclass, field, replace
from importlib import resources
from typing import Callable, Protocol

from . import harden, phrasebook, scripture, symbolic
from .kb import KnowledgeBase, load
from .neural import Guard
from .langid import detect

Message = dict  # {"role": "system"|"user"|"assistant", "content": str}


@dataclass
class Violation:
    proposition: str
    source: str                  # "symbolic" | "neural" | "creed-claim" | "creed-silence"
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
_ANCHOR = re.compile(r"\b(?:SON|FATHER|SPIRIT|GOD|TRINITY|gods?|divine|divinity|deity|resurrection|resurrected|risen|tomb|virgin|creed|heaven|hell|death|dead|die|died|cross|crucif\w*|incarnat\w*|creat\w*|creature|prophet|messiah|kingdom|judge\w*|baptis\w*|church|eucharist|salvation|sin|sins|soul|angel|world|universe|matter|myth|metaphor|persons?|modes?|trinidad|trindade|dios|deus|padre|pai|hijo|filho|personas?|pessoas?|santo)\b|[^\x00-\x7f]", re.I)


_HEADING = re.compile(r"^\s*(?:#{1,6}\s|\*\*[^*]{1,60}\*\*:?\s*$|[-*]\s+\*\*[^*]{1,40}\*\*:?\s*$)")


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
        # es/pt/de: the rules read a phrase-level English pivot (sentence boundaries are kept);
        # the guard and the report keep the original text
        sym_text = phrasebook.pivot(text, lang) if lang in phrasebook.LANGS else text
        sym_claims = symbolic.extract(sym_text, self.kb.extra_patterns) if self.mode != "neural" else []
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
                # Markdown headings ("### The Holy Spirit") and bare fragments carry no claim.
                if _HEADING.match(raw) or len(raw.split()) < 3:
                    anchored = False
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
        for raw in raw_sents:
            lid = self._creed_claim(raw)
            if lid:
                topic = next(t["topic"] for t in self.kb.latitude if t["id"] == lid)
                flags.append(Violation(lid, "creed-claim", 1.0, raw, [], [
                    f"says the Creed settles a question it leaves open ({lid}: {topic}); "
                    "the Creed of 381 does not decide this"]))
            sil = self._creed_silence(raw)
            if sil:
                # Saying a core article is an open question is itself a departure from it: it
                # triggers a repair. On a non-core point it is a flag.
                p = self.kb.proposition(sil)
                v = Violation(sil, "creed-silence", 1.0, raw, [], [
                    f"says the Creed leaves open a point it decides ({sil}: {p.text[:80]})"], p.severity)
                (violations if p.severity == "core" else flags).append(v)
        refs = scripture.find(text)
        if self.bible is not None:
            scripture.check_quotes(text, self.bible, refs)
        ref_problems = [r for r in refs if not r.exists or (r.quote_similarity is not None and r.quote_similarity < self.min_quote_similarity)]
        decision = "block" if violations else ("flag" if flags or ref_problems else "pass")
        return Verdict(decision, violations, flags, sorted(affirmed), report, (time.perf_counter() - t0) * 1000,
                       [asdict(r) | {"canonical": r.canonical} for r in refs], obfuscated)

    # Words that identify a latitude topic when a sentence claims the Creed decides it.
    _LATITUDE_CUES = {
        "L01": r"filioque|proceeds? from the father and the son|proceeds? from (?:both )?the father and (?:from )?the son|double procession",
        "L02": r"chalcedon|two natures|miaphysit\w*",
        "L03": r"baptis\w*|infants?|babies|immersion|sprinkl\w*",
        "L04": r"eucharist|communion|lord's supper|mass|transubstantiation|real presence",
        "L05": r"pope|papacy|papal|bishops?|church government|apostolic succession|ordination|ordain\w*",
        "L06": r"immaculate|assumption|perpetual virginity|intercession of mary|marian",
        "L07": r"justification|faith alone|sola fide|predestination|free will|purgatory",
        "L08": r"sola scriptura|scripture alone|canon|apocrypha|deuterocanon\w*|tradition",
        "L09": r"evolution|evolutionary|young earth|old earth|big bang|six days",
        "L10": r"rapture|millenni\w*|tribulation|purgatory|hell is|annihilation\w*",
        "L11": r"tongues|speaking in tongues|cessation\w*|charismatic|healing",
    }
    _CREED_SAYS = re.compile(r"\b(?:nicene )?creed\b[^.;]{0,40}\b(?:affirms|affirm|states|says|teaches|requires|supports|endorses|mandates|confirms|holds|declares|establishes)\b", re.I)
    _NEGATED = re.compile(r"\b(?:not|n't|no|neither|nor|never|nothing|silent|leaves? open|does not address)\b", re.I)

    def _creed_claim(self, sentence: str) -> str | None:
        """A sentence that says the Creed decides a latitude question (for example "the Nicene
        Creed affirms infant baptism"). Models invent this; it is a flag, never a block."""
        m = self._CREED_SAYS.search(sentence)
        if not m or self._NEGATED.search(sentence):
            return None
        # the Creed's own words about baptism and the church are not a latitude claim
        tail = re.sub(r"one baptism(?: for the (?:forgiveness|remission) of sins)?|one,? holy,? catholic,? and apostolic church",
                      "", sentence[m.start():].lower())
        for lid, cue in self._LATITUDE_CUES.items():
            if re.search(r"\b(?:" + cue + r")\b", tail):
                return lid
        return None

    _CREED_SILENT = re.compile(
        r"(?:\b(?:nicene )?creed\b[^.;]{0,40}?\b(?:does not|doesn't|did not|didn't|never|is silent|says nothing|makes no claims?)"
        r"|\b(?:dust|i|we|this assistant)\b[^.;]{0,20}?\b(?:cannot|can't|can not|am unable to|is unable to|are unable to|won't)(?: (?:affirm or deny|confirm or deny|say|decide|determine|tell you)))"
        r"(?: (?:directly |explicitly |specifically )?(?:make (?:any )?claims?|say(?: anything)?|address|mention|speak|comment|decide|settle|state(?: anything)?|teach(?: anything)?))?"
        r"[^.;]*?\b(?:about|on|whether|regarding|concerning)\b\s*", re.I)

    def _creed_silence(self, sentence: str) -> str | None:
        """The mirror of `_creed_claim`: a sentence that says the Creed does not address a point
        it does decide ("the Creed does not address whether Jesus was created"). A flag only."""
        m = self._CREED_SILENT.search(sentence)
        if not m:
            return None
        rest = sentence[m.end():]
        rest = re.sub(r"^(?:the (?:question|issue|idea|concept|identity) of\s+)?(?:[^,]*,\s*including\s+)?(?:whether\s+)?", "", rest, flags=re.I)
        claims = [replace(c, stance="assert") for c in symbolic.extract(rest, self.kb.extra_patterns)]
        if not claims:
            return None
        res = symbolic.infer(claims, self.kb)
        if res.contradictions:
            return res.contradictions[0].proposition
        if res.affirmed:
            return sorted(res.affirmed)[0]
        return None

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
    def wrap(self, backend: Backend | Callable[[list[Message]], str], max_repairs: int = 2,
             refuse_requires_proof: bool = True, behaviour: str = "enforce") -> "AlignedModel":
        return AlignedModel(self, backend, max_repairs, refuse_requires_proof, behaviour)


@dataclass
class AlignedResponse:
    content: str
    verdict: Verdict
    attempts: int
    repaired: bool
    refused: bool
    drafts: list[str]
    draft_verdicts: list[Verdict] = field(default_factory=list)


BEHAVIOURS = ("enforce", "annotate", "explain")


class AlignedModel:
    """generate -> check -> act, by behaviour:

    enforce   repair with a citation of the article; refuse (with what the Creed confesses)
              only when a proof survives every repair. The default.
    annotate  return the model's first answer unchanged, with its verdict. For review tools
              and for apps that decide for themselves what to show.
    explain   return the model's first answer, and when it crosses or touches the boundary,
              append a short note naming the article and what the Creed confesses.
    """

    def __init__(self, layer: Layer, backend, max_repairs: int = 2, refuse_requires_proof: bool = True,
                 behaviour: str = "enforce"):
        if behaviour not in BEHAVIOURS:
            raise ValueError(f"behaviour must be one of {BEHAVIOURS}")
        self.behaviour = behaviour
        self.refuse_requires_proof = refuse_requires_proof
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
        verdicts: list[Verdict] = []
        verdict = None
        guard_repairs_used = False
        if self.behaviour != "enforce":
            draft = self._gen(convo)
            verdict = self.layer.check(draft)
            content = draft if self.behaviour == "annotate" else draft + self._explain_note(verdict)
            return AlignedResponse(content, verdict, 1, False, False, [draft], [verdict])
        for attempt in range(self.max_repairs + 1):
            draft = self._gen(convo)
            drafts.append(draft)
            verdict = self.layer.check(draft)
            verdicts.append(verdict)
            if verdict.ok:
                return AlignedResponse(draft, verdict, attempt + 1, attempt > 0, False, drafts, verdicts)
            guard_only = all(v.source == "neural" for v in verdict.violations)
            if self.refuse_requires_proof and guard_only:
                # Only the learned guard objects. On real model prose it is often wrong (see
                # docs/findings.md, end-to-end results), so it never causes a refusal. It may
                # ask for one rewrite (run 2 showed a real Spanish modalist answer that only
                # the guard saw); if that does not satisfy it, the answer goes out flagged.
                if guard_repairs_used or attempt == self.max_repairs:
                    flagged = replace(verdict, decision="flag", violations=[], flags=verdict.violations + verdict.flags)
                    return AlignedResponse(draft, flagged, attempt + 1, attempt > 0, False, drafts, verdicts)
                guard_repairs_used = True
            convo = convo + [{"role": "assistant", "content": draft},
                             {"role": "system", "content": self._repair_note(verdict, tentative=guard_only)}]
        fallback = self._fallback(verdict)
        # the verdict reported is the one for the text actually returned
        return AlignedResponse(fallback, self.layer.check(fallback), len(drafts), False, True, drafts, verdicts)

    def _repair_note(self, verdict: Verdict, tentative: bool = False) -> str:
        if tentative:
            lines = ["A check suggests your previous draft may state, as your own view, something the Creed "
                     "of 381 excludes. If it does, rewrite those sentences. If it does not, give the same answer, "
                     "stated plainly. Answer in the language of the question."]
        else:
            lines = ["Your previous draft states, as your own view, something the Creed of 381 excludes. Rewrite it."]
        for v in verdict.violations:
            p = self.layer.kb.proposition(v.proposition)
            if v.source == "creed-silence":
                lines.append(f'- "{v.sentence}" treats as open a point the Creed confesses ({p.id}): {p.text}')
            else:
                lines.append(f'- "{v.sentence}" conflicts with {p.id}: {p.text}')
        lines.append("You may describe other views as reported views (\"Arius taught that ...\"), "
                     "but do not assert them. Keep everything else that was correct.")
        return "\n".join(lines)

    def _explain_note(self, verdict: Verdict) -> str:
        """A short note appended in `explain` mode; empty when nothing touches the boundary."""
        kb = self.layer.kb
        crossed = sorted({v.proposition for v in verdict.violations if v.proposition.startswith("P")})
        doubtful = sorted({v.proposition for v in verdict.flags if v.proposition.startswith("P")} - set(crossed))
        open_q = sorted({v.proposition for v in verdict.violations + verdict.flags if v.proposition.startswith("L")})
        if not (crossed or doubtful or open_q):
            return ""
        out = ["", "", "---", "Note from Dust (Nicene Creed, 381):"]
        for pid in crossed:
            out.append(f"- Part of this answer conflicts with what the Creed confesses: {kb.proposition(pid).text}")
        for pid in doubtful:
            out.append(f"- Part of this answer may not fit what the Creed confesses: {kb.proposition(pid).text}")
        for lid in open_q:
            topic = next((t["topic"] for t in kb.latitude if t["id"] == lid), lid)
            out.append(f"- The Creed of 381 leaves this question open between traditions: {topic}.")
        return "\n".join(out)

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
