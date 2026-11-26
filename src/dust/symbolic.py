"""Symbolic track: a small, transparent semantic parser and forward-chaining checker.

Pipeline for a piece of text:

1. ``normalise``: lower-case, expand contractions, map names of the divine persons to
   entity tokens (SON, FATHER, SPIRIT, GOD) and resolve a sentence-initial "he".
2. ``stance``: decide whether each sentence is the speaker's own assertion, a reported
   view ("Arius taught that ..."), a question, a hypothetical, or a rejection
   ("It is false that ...", which flips polarity).
3. ``extract``: match claim patterns (subject, gap, predicate). Negators in the gap flip
   the literal; a contrastive conjunction ("but", "rather") resets the count.
4. ``infer``: close the asserted literals under the rules in rules.json and report any
   derived literal whose negation is an axiom of the Creed, with a proof chain.

This is deliberately English-only and pattern-based. It is precise where it fires and
silent elsewhere; the neural track covers paraphrase. Its value is that every block it
causes comes with a human-readable proof that cites the article of the Creed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from .kb import KnowledgeBase, load, negate

# --------------------------------------------------------------------------- normalise

_CONTRACTIONS = {
    r"\bisn't\b": "is not", r"\bwasn't\b": "was not", r"\baren't\b": "are not",
    r"\bweren't\b": "were not", r"\bdoesn't\b": "does not", r"\bdidn't\b": "did not",
    r"\bdon't\b": "do not", r"\bwon't\b": "will not", r"\bcan't\b": "can not",
    r"\bcannot\b": "can not", r"\bcouldn't\b": "could not", r"\bshouldn't\b": "should not",
    r"\bhasn't\b": "has not", r"\bhaven't\b": "have not", r"\bhadn't\b": "had not",
    r"\bwouldn't\b": "would not", r"\bit's\b": "it is", r"\bhe's\b": "he is",
}

# Longest aliases first. Applied to lower-cased text.
_ENTITIES = [
    ("TRINITY", [r"the (?:holy |blessed )?trinity", r"the triune god", r"the godhead"]),
    ("SPIRIT", [r"the holy spirit", r"holy spirit", r"the holy ghost", r"holy ghost",
                r"the spirit of god", r"god's spirit", r"god the spirit", r"the paraclete",
                r"the comforter", r"the spirit"]),
    ("FATHER", [r"god the father", r"the heavenly father", r"the father", r"father(?=,? (?:the )?son\b)"]),
    ("SON", [r"the lord jesus christ", r"jesus of nazareth", r"jesus christ", r"the lord jesus",
             r"god the son", r"the son of god", r"the son of man", r"the son", r"the logos",
             r"the word of god(?= (?:became|was made|is|was|existed|took))", r"the word(?= (?:became|was made|is|was|existed|took|of life))",
             r"the messiah", r"jesus", r"christ", r"yeshua", r"(?<=FATHER, )son", r"(?<=FATHER and )son"]),
    ("GOD", [r"almighty god", r"god almighty", r"\bgod\b(?!s\b|'s\b)"]),
]
_ENTITY_RES = [(tok, re.compile(r"\b(?:" + "|".join(alts) + r")\b" if not alts[0].startswith("\\b") else "|".join(alts)))
               for tok, alts in _ENTITIES]

_SENT_SPLIT = re.compile(r"(?<=[.!?;])\s+|\n+")
_PRONOUN = re.compile(r"^(?:and |but |yet |so )?(he|him|his)\b")


_LIST_SPIRIT = re.compile(r"(?<=SON, and )spirit\b|(?<=SON and )spirit\b|(?<=SON, )spirit\b")


def _entity_pass(s: str) -> str:
    for tok, rx in _ENTITY_RES:
        s = rx.sub(tok, s)
    return _LIST_SPIRIT.sub("SPIRIT", s)


def normalise(text: str) -> list[str]:
    """Return normalised sentences with entity tokens."""
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.lower()
    for rx, rep in _CONTRACTIONS.items():
        t = re.sub(rx, rep, t)
    t = re.sub(r"\bn't\b", " not", t)
    sentences = [s.strip() for s in _SENT_SPLIT.split(t) if s and s.strip()]
    out: list[str] = []
    last_entity: str | None = None
    prev_persons = 0
    for s in sentences:
        s = _entity_pass(s)
        if prev_persons >= 2:
            s = re.sub(r"^(?:and |but |yet |so )?they\b", "FATHER, SON and SPIRIT", s)
        m = _PRONOUN.match(s)
        if m:
            # An unresolved sentence-initial "he" in a doctrinal text is taken to be the
            # Son. This is a heuristic and is documented as a limitation.
            rep = (last_entity or "SON") + ("'s" if m.group(1) == "his" else "")
            s = s[: m.start(1)] + rep + s[m.end(1):]
        ents = re.findall(r"\b(SON|SPIRIT|FATHER)\b", s)
        prev_persons = len(set(ents))
        if ents:
            last_entity = ents[0]  # the subject of the previous sentence, usually
        out.append(s)
    return out


# --------------------------------------------------------------------------- stance

_THIRD_PARTY_VERB = r"(?:taught|teach|teaches|believed|believe|believes|claimed|claim|claims|argued|argue|argues|held|hold|holds|maintained|maintain|maintains|said|say|says|thought|think|thinks|insisted|insist|insists|asserted|assert|asserts|suggested|suggest|suggests|proposed|denied|deny|denies|contended|contend|contends|alleged|allege|alleges|concluded|conclude|concludes|wrote|write|writes|proposed|propose|proposes|hypothesi[sz]ed|speculated|reported|reports|regarded|regard|regards|considered|consider|considers|viewed|view|views)"
_REPORTED = [
    re.compile(r"\b(?:seminar|council|synod|school|sect|movement|party|scholar|critic|historian|theologian)s?\b[^.;]*\b" + _THIRD_PARTY_VERB + r"\b"),
    re.compile(r"\b(?!i\b|we\b|christians\b|church\b|christianity\b|theology\b|creed\b|scripture\b|bible\b)(\w+)\s+(?:\w+\s+)?" + _THIRD_PARTY_VERB + r"\s+that\b"),
    re.compile(r"\baccording to (?!scripture|the scriptures|the creed|the bible|the gospels?|the apostles?|the council|the fathers|SON)"),
    re.compile(r"\b(?:in (?:the|their|his|her) view|on (?:this|that|their|his) view|from (?:their|his|her) perspective)\b"),
    re.compile(r"\b(?:arius|arians?|sabellius|sabellians?|modalists?|docetists?|docetic|gnostics?|gnosticism|marcion(?:ites)?|apollinari(?:us|ans?)|ebionites?|macedonians?|pneumatomachians?|adoptionists?|nestori(?:us|ans?)|heretics?|heresy|heresies|heretical|unitarians?)\b"),
    re.compile(r"\b(?:was|were|is|are) (?:condemned|rejected|anathemati[sz]ed|refuted|excluded)\b"),
    re.compile(r"\bthe (?:view|idea|claim|teaching|notion|position|belief|theory|doctrine|argument) (?:that|of)\b"),
    re.compile(r"\b(?:some|many|other|certain|liberal|skeptical|sceptical|critical) (?:people|scholars|groups|christians|theologians|critics|traditions|writers|sects)\b"),
    re.compile(r"\b(?:critics|skeptics|sceptics|scholars|historians|atheists|muslims|the quran|islam|jews|judaism|unitarianism)\b"),
    re.compile(r"\b(?:would|might|could) (?:say|argue|claim)\b"),
]
_QUESTION_START = re.compile(r"^(?:is|was|are|were|did|does|do|can|could|should|would|will|why|how|what|who|which|whether|has|have)\b")
_HYPOTHETICAL = re.compile(r"^(?:if|suppose|supposing|imagine|what if|even if|assuming)\b")
_REJECTION = re.compile(
    r"\b(?:it is (?:not true|false|wrong|untrue|incorrect|a mistake|an error|a heresy|heretical|unbiblical|not biblical|not the case)"
    r"(?: to (?:say|claim|think|believe|teach))?(?: that)?"
    r"|no one (?:can|should|may|could) (?:say|claim|think|believe|teach)(?: that)?"
    r"|(?:i|we|christians|the church|the creed|scripture|the scriptures|the bible|the council|the fathers|orthodoxy|the nicene creed)"
    r" (?:firmly |also |clearly |rightly )?(?:reject|rejects|rejected|deny|denies|denied|refute|refutes|refuted|exclude|excludes|excluded|rule out|rules out|ruled out)"
    r"(?: the (?:view|idea|claim|teaching|notion|position|belief) )?(?: that)?)\b"
)


# "the Son is a creature, as the Arians believe": a trailing aside endorses, it does not report
_ENDORSE = re.compile(r"^(?!\W*(?:as |according to ))[^,;]{8,},? (?:just )?as (?:the |some |many )?\w+ (?:also )?(?:believe|believed|teach|taught|held|hold|say|said|claim|claimed|argue|argued)\b")
# "the question of whether X is a matter of interpretation": X is not asserted
_EMBEDDED_Q = re.compile(r"\b(?:the question|questions?|asking|ask|debate|debates|debated|unclear|uncertain) (?:of |about |over |as to )?whether\b|\bwhether or not\b")


def stance(sentence: str, raw: str = "") -> str:
    """One of: assert, reject, reported, question, hypothetical."""
    s = sentence
    if raw.strip().endswith("?") or s.endswith("?") or _QUESTION_START.match(s) or _EMBEDDED_Q.search(s):
        return "question"
    if _ENDORSE.search(s):
        return "assert"
    if _HYPOTHETICAL.match(s):
        return "hypothetical"
    rej = _REJECTION.search(s)
    rep = min((m.start() for m in (rx.search(s) for rx in _REPORTED) if m), default=None)
    # An attribution that frames the whole sentence ("Arius taught that it is wrong to
    # say ...") wins over a rejection inside it; otherwise a rejection wins.
    if rej and (rep is None or rej.start() < rep):
        return "reject"
    if rep is not None:
        return "reported"
    return "assert"


# --------------------------------------------------------------------------- patterns

_NEG = re.compile(r"\b(?:not|never|no|neither|nor|nothing|in no way|by no means|hardly|nobody)\b")
_CONTRAST = re.compile(r"\b(?:but|rather|instead|yet|although|though|whereas|while)\b")
_COP = r"(?:is|was|are|were|be|been|being|remains|remained)"
_ADV = r"(?:\W+(?:not|never|truly|fully|really|actually|completely|wholly|very|true|a|an|the|always|indeed|also|both|just|only|merely|simply|eternally|in fact)){0,4}"


@dataclass(frozen=True)
class Pattern:
    literal: str          # literal asserted when the pattern matches without negation
    regex: re.Pattern
    fixed: bool = False   # polarity built into the pattern; ignore gap negators


def _cop(subj: str, nominal: str, literal: str, gap: int = 4) -> Pattern:
    rx = (r"\b" + subj + r"\b(?P<gap>(?:\W+\w+){0," + str(gap) + r"}?)\W+" + _COP +
          r"(?P<gap2>" + _ADV + r")\W+(?:" + nominal + r")\b")
    return Pattern(literal, re.compile(rx))


def _verb(subj: str, verb: str, literal: str, gap: int = 5) -> Pattern:
    rx = r"\b" + subj + r"\b(?P<gap>(?:\W+\w+){0," + str(gap) + r"}?)\W+(?:" + verb + r")\b"
    return Pattern(literal, re.compile(rx))


def _fixed(rx: str, literal: str) -> Pattern:
    return Pattern(literal, re.compile(rx), fixed=True)


def _free(rx: str, literal: str) -> Pattern:
    """Pattern with optional negation anywhere before the match inside the sentence."""
    return Pattern(literal, re.compile(r"(?P<gap>^.{0,60}?)" + rx))


S, SP, F, G = "SON", "SPIRIT", "FATHER", "GOD"
_PERSONS = r"(?:FATHER|SON|SPIRIT)"
_MADE_NOT_INCARNATION = r"(?:created|made)(?!\W+(?:man|flesh|human|known|perfect|lord|sin|like|a little|incarnate|alive|manifest|higher|heir|king))"

PATTERNS: list[Pattern] = [
    # ---- Son: creature, eternity, begetting (E01, E04)
    _fixed(r"\bthere was (?:a time|once|a point) when SON (?:was not|did not exist|was not yet)\b", "-eternal(SON)"),
    _cop(S, r"(?:the |a |an )?(?:first |highest |greatest |most exalted )?(?:created being|creature|creation|created|thing (?:that )?GOD made|thing (?:that )?FATHER made)", "created(SON)"),
    _verb(S, _MADE_NOT_INCARNATION + r"(?=\W*(?:$|by\b|as\b|before\b|in time\b|at\b|from\b|out of\b|,|\.|;|and\b|but\b|like\b))|brought into existence|produced by|formed by", "created(SON)"),
    _cop(S, r"the (?:very )?first (?:\w+ ){0,3}(?:GOD|he|FATHER) (?:ever )?(?:made|created|produced)", "created(SON)"),
    _verb(G, r"(?:created|made|produced) (?:his|the) (?:only |first |beloved )?son\b", "created(SON)", gap=3),
    _fixed(r"\bthere was never a (?:time|moment|point) when SON (?:was not|did not exist|was not yet)\b", "eternal(SON)"),
    _verb(G, r"(?:created|made|produced) SON\b", "created(SON)", gap=3),
    _verb(F, r"(?:created|made|produced) SON\b", "created(SON)", gap=3),
    _cop(S, r"(?:an |the |a )?(?:\w+ )?(?:angel|archangel|michael the archangel)", "angel(SON)"),
    _cop(S, r"(?:eternal|co-?eternal|eternally begotten|without beginning|pre-?existent|everlasting)", "eternal(SON)"),
    _verb(S, r"(?:has always existed|always existed|existed (?:from|before) (?:all )?(?:eternity|time|the ages|ages|creation|the world|the foundation)|existed eternally|has no beginning|had no beginning)", "eternal(SON)"),
    _verb(S, r"(?:had a beginning|has a beginning|began to exist|came into (?:being|existence)|did not (?:always )?exist before)", "-eternal(SON)"),
    _cop(S, r"(?:the )?(?:only[- ])?begotten(?: son)?(?: of (?:FATHER|GOD))?", "begotten(SON)"),
    _verb(S, r"(?:became|become|becomes) (?:\w+ ){0,2}(?:GOD|divine|SON|the son)|was adopted|was exalted to (?:divinity|divine status|godhood)|earned (?:divinity|divine status)", "adopted(SON)"),
    _fixed(r"\bGOD adopted SON\b", "adopted(SON)"),
    # ---- Son: divinity (E05) and consubstantiality (E02)
    _cop(S, r"(?:fully |truly |very |true |really |himself )?(?:GOD|divine|deity|GOD incarnate|GOD in the flesh|the second person of the TRINITY|lord and GOD)(?!\W+(?:'s|of the old))", "divine(SON)"),
    _cop(S, r"(?:just |only |merely |simply |nothing (?:more|other) than |no more than |not more than )(?:a |an )?(?:\w+ )?(?:man|human|human being|prophet|teacher|rabbi|moral teacher|philosopher|guru|sage|mortal|messenger|example|revolutionary|healer)", "mere_human(SON)"),
    _cop(S, r"(?:a |an )?(?:mere|ordinary|normal|regular) (?:man|human|human being|mortal|prophet|teacher)", "mere_human(SON)"),
    _cop(S, r"(?:a GOD|a lesser (?:GOD|divinity|deity)|a (?:secondary|subordinate|second|lesser|minor|demi-?) ?(?:GOD|deity|divinity)|a demigod|less (?:divine|GOD) than FATHER|inferior to FATHER in (?:being|essence|nature|divinity)|of (?:a )?(?:similar|like|different) (?:substance|essence|being|nature)(?: to| as| from)? FATHER|(?:only )?like FATHER in (?:being|essence|substance|nature)|divine (?:only )?in a (?:lesser|lower|derived|secondary|subordinate)(?:,? (?:lesser|lower|derived|secondary|subordinate))? (?:degree|sense|way|measure))", "lesser_god(SON)"),
    _cop(S, r"(?:of (?:one|the same) (?:substance|essence|being|nature) (?:with|as) FATHER|consubstantial(?: with FATHER)?|homoousios|equal (?:to|with) FATHER(?: in (?:being|essence|nature|divinity|glory))?|co-?equal(?: with FATHER)?)", "consubstantial(SON)"),
    _verb(S, r"(?:shares|shared) (?:the same|one) (?:substance|essence|being|nature|divinity) (?:with|as) FATHER", "consubstantial(SON)"),
    # ---- Son and creation (E16)
    _fixed(r"\ball things were made (?:through|by) SON\b", "agent_of_creation(SON)"),
    _verb(S, r"(?:created|made) (?:all things|everything|the world|the universe|the cosmos)|through whom all things were made", "agent_of_creation(SON)"),
    _verb(S, r"(?:had|has|played) no (?:part|role|share) in (?:creation|creating)", "-agent_of_creation(SON)"),
    _fixed(r"\bthe (?:world|universe) was (?:made|created) (?:before|without) SON\b", "-agent_of_creation(SON)"),
    # ---- Incarnation, virgin birth, humanity (E07, E08, E12)
    _verb(S, r"(?:became|was made|took on|assumed|took) (?:human )?flesh|became (?:a |truly |fully )?(?:man|human)|was incarnate|came down from heaven|was made man", "incarnate(SON)"),
    _cop(S, r"(?:fully |truly |really |completely |perfectly )(?:human|man|a man)", "human(SON)"),
    _verb(S, r"(?:only |merely )?(?:seemed|appeared|pretended) (?:to (?:be|have|suffer|die)|human|as a man)|had (?:only )?(?:a phantom|an illusory|an apparent|no real|no physical|no true) (?:body|flesh|humanity)", "seemed_human(SON)"),
    _cop(S, r"(?:only |merely |just )?(?:a phantom|an illusion|a hologram|a spirit without a body|a ghost)", "seemed_human(SON)"),
    _verb(S, r"had no human (?:mind|soul|will|intellect|spirit)|lacked a human (?:mind|soul|will|intellect)", "no_human_mind(SON)"),
    _fixed(r"\bthe (?:divine )?(?:word|logos|divinity) (?:replaced|took the place of) (?:SON's |his |the )?human (?:mind|soul)", "no_human_mind(SON)"),
    _verb(S, r"born of (?:a |the )?virgin(?: mary)?|conceived by (?:the power of )?SPIRIT|virginally conceived|incarnate (?:by|of) SPIRIT", "virgin_birth(SON)"),
    _fixed(r"\b(?:joseph was (?:SON's|the|his) (?:biological|real|natural|actual) father|SON (?:had|has) a (?:human|biological) father|(?:biological|natural) son of joseph|mary was not a virgin|mary conceived (?:SON )?(?:in the (?:normal|ordinary|natural|usual) way|naturally|with joseph)|SON was conceived (?:in the (?:normal|ordinary|natural|usual) way|naturally|normally)|(?:conceived|born) (?:\w+ ){0,4}with a (?:human|biological|natural|earthly) father)\b", "-virgin_birth(SON)"),
    _fixed(r"\bthe virgin birth (?:is|was) (?P<neg>not |never )?(?:just |only |merely |simply )?(?:a |an )?(?:myth|legend|fable|fiction|invention|later invention|metaphor|symbol|pious story|story)\b", "-virgin_birth(SON)"),
    _fixed(r"\bthe virgin birth (?:never happened|did not happen|is not historical|is unhistorical)\b", "-virgin_birth(SON)"),
    # ---- History, cross, death (E07, E13)
    _fixed(r"(?<!when )(?<!before )\bSON (?:never existed|never lived|did not (?:really )?exist|(?:is|was) (?:a |an )?(?:myth|fictional character|invention|legend))\b", "-historical(SON)"),
    _verb(S, r"(?:crucified|nailed to the cross|put to death|executed)", "crucified(SON)"),
    _verb(S, r"(?:truly |really |actually )?(?:died|die|suffered and died|suffered and was buried|was buried|tasted death|suffer and die)", "died(SON)"),
    _fixed(r"\bSON\b[^.;]*?\brather than (?:a |the )?(?:divine (?:being|person)|GOD)\b", "-divine(SON)"),
    _fixed(r"\bSON\b[^.;]*?\bbut (?:was |is )?not (?:fully |truly |really |actually )?(?:GOD|divine)\b", "-divine(SON)"),
    _verb(S, r"(?:swooned|swoon|fainted|faint|only appeared to die|merely appeared to die|survived the (?:cross|crucifixion)|survive the (?:cross|crucifixion)|was revived in the tomb|revived in the tomb|taken down (?:from the cross )?alive|recovered in the tomb)", "swoon(SON)"),
    _fixed(r"\b(?:someone else|another man|judas|simon of cyrene|a lookalike|a double) (?:was crucified|died) (?:in SON's place|instead of SON|in his place)\b", "substitute(SON)"),
    _fixed(r"\bSON was (?:not crucified|never crucified)(?: but| and)\b.*\b(?:someone else|another|in his place|substitute)", "substitute(SON)"),
    # ---- Resurrection, ascension, return, kingdom (E11, E13, E14)
    _verb(S, r"(?:bodily |physically |truly |really |actually )?(?:rose|rise|raised|is risen|has risen|resurrected|came back to life|come back to life|conquered death|rose bodily|rose again|raised from the dead)", "rose(SON)", gap=8),
    _verb(r"SON's body", r"(?:raised|rose|came back to life|was raised)", "rose(SON)", gap=4),
    _fixed(r"\b(?:the )?body of SON (?:decayed|rotted|remained|stayed|lies|lay|is still)\b", "-rose(SON)"),
    _fixed(r"\bSON (?:lives|lived) on (?:only )?in (?:our|their|the|his followers') (?:memories|memory|hearts|minds)\b", "-rose(SON)"),
    _fixed(r"\b(?:resurrection|easter) (?:stories|accounts|narratives) are (?:\w+ ){0,2}(?:myths|legends|fables|fictions|metaphors|symbols)\b", "-rose(SON)"),
    _fixed(r"\btalk of SON (?:returning|coming (?:again|back))[^.;]*\b(?:mythology|myth|metaphor)\b", "-will_return(SON)"),
    _fixed(r"\b\w+,? not SON,? (?:who |that )?(?:was crucified|died)\b|\bit was \w+,? not SON\b", "substitute(SON)"),
    _fixed(r"\b(?:the |SON's |his )?resurrection(?: of SON)? (?:is|was) (?P<neg>not |never |in no way )?(?:just |only |merely |simply |really |purely |best understood as )?(?:a |an )?(?:metaphor|myth|legend|symbol|symbolic|spiritual (?:idea|experience|truth|event)|hallucination|vision|fiction|story|way of speaking|poetic)\b", "-rose(SON)"),
    _fixed(r"\b(?:SON's|his) (?:body|corpse|bones) (?:stayed|remained|rotted|decayed|is still|lies|lay) (?:in the (?:tomb|grave|ground)|buried)", "-rose(SON)"),
    _fixed(r"\bSON (?:rose|was raised|lives on) only (?:spiritually|in (?:the )?(?:hearts|memory|minds|faith))\b", "-rose(SON)"),
    _fixed(r"\bthe (?:tomb|grave) was not empty\b", "-rose(SON)"),
    _verb(S, r"ascended|was taken up into heaven|sits at the right hand|is seated at the right hand", "ascended(SON)"),
    _verb(S, r"(?:come|return|coming) again|return\b(?! to (?:galilee|jerusalem|nazareth|capernaum))|coming back|come back", "will_return(SON)", gap=3),
    _fixed(r"\bthere (?:is|will be) no second coming\b|\bthe second coming (?:is|was) (?P<neg>not )?(?:just |only |merely )?(?:a )?(?:myth|metaphor|symbol|fiction)\b|\bSON (?:is|will) never (?:coming|come) back\b", "-will_return(SON)"),
    _verb(S, r"judge (?:the )?(?:living|quick|world|nations|dead)", "judge(SON)", gap=3),
    _fixed(r"\bthere (?:is|will be) no (?:final |last )?(?:judgement|judgment|day of judgement|day of judgment)\b", "-judge(SON)"),
    _fixed(r"\b(?:SON's|his) kingdom will (?:have no end|never end|last forever|endure forever|be everlasting)\b", "kingdom_endless(SON)"),
    _fixed(r"\b(?:SON's|his) (?:kingdom|reign|rule) will (?:come to an end|end|cease|be handed back and cease|finish)\b", "-kingdom_endless(SON)"),
    _fixed(r"\b(?:SON's|his) (?:kingdom|reign) (?:is|will be) (?:temporary|not eternal|not everlasting)\b", "-kingdom_endless(SON)"),
    # ---- Holy Spirit (E06)
    _cop(SP, r"(?:the |a )?(?:lord|divine person|person|GOD|divine|fully GOD|truly GOD|third person of the TRINITY|giver of life)", "lord(SPIRIT)"),
    _cop(SP, r"(?:just |only |merely |simply |nothing more than |not a person but )?(?:an |a |GOD's )?(?:impersonal|active|mere|invisible) (?:force|power|energy|influence)|(?:just |only |merely |simply )(?:a |an |GOD's )?(?:force|power|energy|influence|it)|an it\b|a thing\b", "impersonal(SPIRIT)"),
    _cop(SP, r"(?:just |only |merely |simply )(?:a |an )?(?:way of (?:talking|speaking) about|name for|metaphor for|figure of speech for|personification of)", "impersonal(SPIRIT)"),
    _cop(SP, r"(?:a |the )?(?:created|creature|created being|created power|angel)", "created(SPIRIT)"),
    _verb(SP, r"(?:is|was|should be|must be|is to be|ought to be) (?:worshipped|worshiped|adored|glorified)", "divine(SPIRIT)"),
    _fixed(r"\b(?:we|christians|one) (?:should|must|may|ought to) (?:never |not )worship SPIRIT\b", "-divine(SPIRIT)"),
    _verb(SP, r"proceeds (?:eternally )?from FATHER|proceeded from FATHER", "proceeds_from_father(SPIRIT)"),
    _fixed(r"\bSPIRIT proceeds (?:only |solely )?from SON (?:alone|only)\b|\bSPIRIT (?:does not|did not) proceed from FATHER\b", "-proceeds_from_father(SPIRIT)"),
    _verb(SP, r"spoke (?:through|by) the prophets|inspired the prophets", "inspired_prophets(SPIRIT)"),
    # ---- One God, creator, Trinity (E03, E09, E10)
    _fixed(r"\bthere (?:are|were) (?:three|two|many|several|multiple|countless) gods\b|\b(?:FATHER, SON,? and SPIRIT|the three persons) are three (?:separate |different |distinct )?gods\b|(?<!not )\bthree gods\b(?! but)|\bwe worship three gods\b", "many_gods(GOD)"),
    _fixed(r"\bthere is (?:only )?one GOD\b|\bGOD is one\b", "one_god(GOD)"),
    _fixed(r"\b(?:are|is|were) not three (?:separate |different )?gods\b|\bnot three gods\b", "one_god(GOD)"),
    _verb(G, r"(?:made|created|is the maker of|is the creator of) (?:heaven and earth|the world|all things|everything|the universe|the heavens and the earth)", "creator(GOD)"),
    _fixed(r"\bthe (?:material |physical )?(?:world|universe|cosmos|creation) was (?:made|created|formed) by (?:an? )?(?:evil|lesser|lower|fallen|ignorant|inferior|different|second|rival) (?:GOD|deity|being|power|demiurge|spirit|creator)\b", "demiurge(GOD)"),
    _fixed(r"\b(?:a |the )demiurge (?:made|created|formed|fashioned)\b|\bmatter is (?:inherently |essentially )?evil\b|\bthe GOD of the old testament (?:is|was) (?:not FATHER|not the same|a different|an evil|a lesser|a cruel|an inferior)", "demiurge(GOD)"),
    _fixed(r"\b(?:FATHER,? SON,? and SPIRIT|FATHER and SON|the three) are (?:just |only |merely |simply |really )?(?:three |different )?(?:modes|masks|roles|manifestations|names|titles|forms|faces|offices|aspects|hats|costumes)(?:,? (?:or |and )?(?:modes|masks|roles|manifestations|names|titles|forms|faces|offices|aspects|hats|costumes))* (?:of|for) (?:one|the same|a single)(?: \w+)?\b", "same_person(TRINITY)"),
    # the creedal denial of modalism: "Father, Son and Spirit are not (three) modes of one person"
    _fixed(r"\b(?:(?:the )?FATHER,? (?:the )?SON,? and (?:the )?SPIRIT|the three(?: persons)?|they) are (?:not|never|in no way) (?:just |only |merely |simply )?(?:three )?(?:names|modes|masks|roles|manifestations|titles|forms|faces|aspects)(?: or (?:modes|names|masks|roles|manifestations|forms|aspects))? (?:of|for) (?:one|the same|a single)(?: \w+)?\b", "distinct(TRINITY)"),
    _fixed(r"\bGOD (?:is|was) (?:one person|a single person|one individual|unipersonal)(?: who| that)? (?:appears|manifests|reveals|acts|plays|shows|works)\b|\b(?:one person|the same person) (?:in|with|appearing in|wearing) three (?:modes|roles|masks|forms|manifestations|ways)\b", "same_person(TRINITY)"),
    _fixed(r"\bone (?:actor|person|man|individual) (?:playing|with|wearing) three (?:parts|roles|masks|hats)\b", "same_person(TRINITY)"),
    _cop(S, r"(?:just |simply |merely |really |actually )?(?:FATHER|the same person as FATHER|identical (?:to|with) FATHER)(?! of)", "same_person(TRINITY)"),
    _fixed(r"\bFATHER (?:became|turned into|is) SON\b|\bFATHER (?:died|suffered) on the cross\b", "same_person(TRINITY)"),
    _fixed(r"\b(?:FATHER,? SON,? and SPIRIT|the three persons) are (?:three )?(?:distinct|eternally distinct)(?: persons)?\b|\bthree (?:distinct )?persons\b", "distinct(TRINITY)"),
    # ---- Last things (E15)
    _fixed(r"\bthere (?:is|will be) no (?:resurrection|bodily resurrection|resurrection of the dead|life after death|afterlife|life to come|world to come)\b", "-resurrection_of_dead(ALL)"),
    _fixed(r"\b(?:death is (?:the |simply the )?(?:final |absolute )?end|the dead (?:will not|will never|do not|never) rise|when we die,? we (?:simply )?(?:cease to exist|are gone) (?:forever|permanently|and that is (?:it|the end)))\b", "-resurrection_of_dead(ALL)"),
    _fixed(r"\bthe dead will (?:be raised|rise)\b|\bthe resurrection of the dead\b", "resurrection_of_dead(ALL)"),
    _fixed(r"\bthere is no (?:heaven|new creation|eternal life)\b", "-world_to_come(ALL)"),
]


@dataclass
class Claim:
    literal: str
    sentence_index: int
    stance: str
    span: str

    @property
    def asserted(self) -> bool:
        return self.stance in ("assert", "reject")


def _count_neg(gap: str) -> int:
    parts = _CONTRAST.split(gap)
    return len(_NEG.findall(parts[-1]))


@lru_cache(maxsize=16)
def _compile_extra(spec: tuple) -> list[Pattern]:
    return [Pattern(lit, re.compile(rx), fixed=True) for lit, rx in spec]


def extract(text: str, extra: list[dict] | None = None) -> list[Claim]:
    raw_sentences = [s for s in _SENT_SPLIT.split(text) if s and s.strip()]
    claims: list[Claim] = []
    for i, s in enumerate(normalise(text)):
        st = stance(s, raw_sentences[i] if i < len(raw_sentences) else "")
        seen: set[tuple[str, int]] = set()
        pats = PATTERNS + (_compile_extra(tuple((d["literal"], d["regex"]) for d in extra)) if extra else [])
        for pat in pats:
            for m in pat.regex.finditer(s):
                lit = pat.literal
                if pat.fixed and m.groupdict().get("neg"):
                    lit = negate(lit)
                if not pat.fixed:
                    gap = (m.groupdict().get("gap") or "") + " " + (m.groupdict().get("gap2") or "")
                    if _count_neg(gap) % 2 == 1:
                        lit = negate(lit)
                if st == "reject":
                    lit = negate(lit)
                key = (lit, m.start())
                if key in seen:
                    continue
                seen.add(key)
                claims.append(Claim(lit, i, st, m.group(0)))
    return _drop_subsumed(claims)


def _drop_subsumed(claims: list[Claim]) -> list[Claim]:
    """'Just a man' also matches the plain 'a man' humanity pattern; and 'became God'
    matches the divinity pattern. Keep the more specific claim."""
    by_sent: dict[int, set[str]] = {}
    for c in claims:
        by_sent.setdefault(c.sentence_index, set()).add(c.literal.lstrip("-").split("(")[0])
    out = []
    for c in claims:
        preds = by_sent[c.sentence_index]
        base = c.literal.lstrip("-").split("(")[0]
        if base == "divine" and c.literal == "divine(SON)" and ("adopted" in preds or "lesser_god" in preds):
            continue
        if base == "human" and "mere_human" in preds:
            continue
        out.append(c)
    return out


# --------------------------------------------------------------------------- infer

@dataclass
class Contradiction:
    literal: str              # the offending derived literal
    proposition: str          # Creed proposition id it contradicts
    proof: list[str]          # human-readable chain
    claim: Claim


@dataclass
class SymbolicResult:
    claims: list[Claim] = field(default_factory=list)
    contradictions: list[Contradiction] = field(default_factory=list)
    affirmed: list[str] = field(default_factory=list)   # proposition ids affirmed
    errors: list[str] = field(default_factory=list)     # excluded-error ids implicated

    @property
    def stances(self) -> set[str]:
        return {c.stance for c in self.claims}


def infer(claims: list[Claim], kb: KnowledgeBase | None = None) -> SymbolicResult:
    kb = kb or load()
    res = SymbolicResult(claims=claims)
    rule_index: dict[str, list] = {}
    for r in kb.rules:
        rule_index.setdefault(r.premise, []).append(r)
    implicated: set[str] = set()
    affirmed: set[str] = set()
    for claim in claims:
        if not claim.asserted:
            continue
        # breadth-first closure from this claim, keeping proofs
        frontier = [(claim.literal, [f'claim: "{claim.span}" => {claim.literal}'])]
        visited: set[str] = set()
        while frontier:
            lit, proof = frontier.pop(0)
            if lit in visited:
                continue
            visited.add(lit)
            implicated.add(lit)
            if lit in kb.axioms:
                affirmed.add(kb.axioms[lit])
            neg = negate(lit)
            if neg in kb.axioms:
                pid = kb.axioms[neg]
                p = kb.proposition(pid)
                res.contradictions.append(Contradiction(
                    lit, pid, proof + [f"contradicts {pid} ({neg}): {p.text}"], claim))
            for r in rule_index.get(lit, []):
                for concl in r.conclusions:
                    frontier.append((concl, proof + [f"{r.id}: {lit} -> {concl} ({r.why})"]))
    # de-duplicate contradictions by (literal, proposition)
    uniq = {}
    for c in res.contradictions:
        uniq.setdefault((c.literal, c.proposition), c)
    res.contradictions = list(uniq.values())
    res.affirmed = sorted(affirmed - {c.proposition for c in res.contradictions})
    if res.contradictions:
        primary = {c.claim.literal for c in res.contradictions}
        found = kb.errors_for(primary) or kb.errors_for({c.literal for c in res.contradictions})
        res.errors = [e.id for e in found]
    return res


def analyse(text: str, kb: KnowledgeBase | None = None) -> SymbolicResult:
    kb = kb or load()
    return infer(extract(text, kb.extra_patterns), kb)
