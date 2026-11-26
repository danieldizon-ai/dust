"""A small phrase pivot for Spanish, Portuguese and German, so the symbolic rules can read
the doctrinal core of a sentence in those languages.

It is not a translator. It rewrites the handful of words and phrases the rules depend on
(the divine names, "is not", "a person", "was created", "rose", "only a man", reporting
verbs) into English and leaves everything else alone. A sentence the rules cannot parse
afterwards simply yields no claim, so the cost of a miss is the status quo (guard only).

Written from the non-English answers in the end-to-end runs (results/e2e/) and general
vocabulary. The 20 Spanish, Portuguese and German benchmark items had been seen before it
was written, so its benchmark gain on them is not an independent measurement.
"""
from __future__ import annotations

import re

LANGS = ("es", "pt", "de")

_A = "[aá]"
_E = "[eé]"
_I = "[ií]"
_O = "[oó]"
_U = "[uú]"

# (pattern, replacement), applied in order, case-insensitive. Longer phrases first.
_COMMON_NAMES = [
    (r"\bjesucristo\b|\bjesus cristo\b|\bjesus christus\b", "Jesus Christ"),
    (r"\bjes[uú]s\b", "Jesus"),
    (r"\bcristo\b|\bchristus\b", "Christ"),
]

_ES = [(r"\bson\b", "are"), (r"\bno son\b", "are not")] + _COMMON_NAMES + [
    (r"\bel esp[ií]ritu santo\b|\besp[ií]ritu santo\b", "the Holy Spirit"),
    (r"\bel hijo de dios\b", "the Son of God"),
    (r"\bel hijo\b", "the Son"),
    (r"\bel padre\b", "the Father"),
    (r"\bla trinidad\b", "the Trinity"),
    (r"\bdios\b", "God"),
    (r"\bno (?:era|es|fue)\b", "is not"),
    (r"\b(?:era|es|fue)\b", "is"),
    (r"\bno resucit[oó]\b|\bnunca resucit[oó]\b", "did not rise"),
    (r"\bresucit[oó]\b", "rose"),
    (r"\bfue cread[oa]\b|\bha sido cread[oa]\b|\bhab[ií]a sido cread[oa]\b", "was created"),
    (r"\bcread[oa] por\b", "created by"),
    (r"\buna criatura\b", "a creature"),
    (r"\buna (?:sola|[uú]nica) persona\b", "a single person"),
    (r"\bson are\b", "Son are"),
    (r"\buna persona\b", "a person"),
    (r"\btres personas\b", "three persons"),
    (r"\btres dioses\b|\btres seres divinos\b", "three gods"),
    (r"\buna (?:fuerza|energ[ií]a)\b", "an impersonal force"),
    (r"\bun [aá]ngel\b", "an angel"),
    (r"\bsolo un (?:gran )?(?:hombre|maestro|profeta)\b|\bsolamente un (?:hombre|profeta)\b", "only a man"),
    (r"\bsino\b|\bpero\b", "but"),
    (r"\by\b", "and"),
    (r"\bconsiderad[oa]\b", "considered"),
    (r"\barrio (?:ense[nñ][oó]|afirmaba|dec[ií]a|cre[ií]a)\b", "Arius taught"),
    (r"\b(?:algunos|muchos) creen\b", "some people believe"),
    (r"\bque\b", "that"),
]

_PT = _COMMON_NAMES + [
    (r"\bo esp[ií]rito santo\b|\besp[ií]rito santo\b", "the Holy Spirit"),
    (r"\bo filho de deus\b", "the Son of God"),
    (r"\bo filho\b", "the Son"),
    (r"\bo pai\b", "the Father"),
    (r"\ba trindade\b", "the Trinity"),
    (r"\bdeus\b", "God"),
    (r"\bn[aã]o (?:era|[eé]|foi)\b", "is not"),
    (r"\b(?:era|foi)\b|(?<!\w)é(?!\w)", "is"),
    (r"(?<!\w)e(?!\w)", "and"),
    (r"\bconsiderad[oa]\b", "considered"),
    (r"\bn[aã]o ressuscitou\b|\bnunca ressuscitou\b", "did not rise"),
    (r"\bressuscitou\b", "rose"),
    (r"\bfoi criad[oa]\b|\btinha sido criad[oa]\b", "was created"),
    (r"\bcriad[oa] pelo\b|\bfeit[oa] pelo\b", "created by the"),
    (r"\buma criatura\b", "a creature"),
    (r"\buma (?:s[oó]|[uú]nica) pessoa\b", "a single person"),
    (r"\buma pessoa\b", "a person"),
    (r"\btr[eê]s pessoas\b", "three persons"),
    (r"\btr[eê]s deuses\b", "three gods"),
    (r"\buma (?:for[cç]a|energia)\b", "an impersonal force"),
    (r"\bum anjo\b", "an angel"),
    (r"\bapenas um (?:homem|profeta|mestre)\b|\bs[oó] um (?:homem|profeta)\b", "only a man"),
    (r"\bmas\b", "but"),
    (r"\b[aá]rio (?:ensinou|dizia|afirmava|acreditava)\b", "Arius taught"),
    (r"\b(?:alguns|muitos) acreditam\b", "some people believe"),
    (r"\bque\b", "that"),
]

_DE = _COMMON_NAMES + [
    (r"\bder heilige geist\b|\bden heiligen geist\b|\bheiliger geist\b", "the Holy Spirit"),
    (r"\bder sohn gottes\b", "the Son of God"),
    (r"\bder sohn\b|\bden sohn\b", "the Son"),
    (r"\bder vater\b|\bden vater\b", "the Father"),
    (r"\bdie dreifaltigkeit\b|\bdie dreieinigkeit\b", "the Trinity"),
    (r"\bgott\b", "God"),
    (r"\bist nicht\b|\bwar nicht\b", "is not"),
    (r"\bist\b|\bwar\b", "is"),
    (r"\bnicht (?:von den toten )?auferstanden\b", "did not rise"),
    (r"\bauferstanden\b", "risen"),
    (r"\bwurde (?:von (?:God|Gott) )?(?:erschaffen|geschaffen)\b", "was created"),
    (r"\bein gesch[oö]pf\b", "a creature"),
    (r"\beine (?:einzige )?person\b(?= der| von|\W*$)", "a person"),
    (r"\beine person\b", "a person"),
    (r"\bdrei personen\b", "three persons"),
    (r"\bdrei g[oö]tter\b", "three gods"),
    (r"\beine (?:kraft|energie)\b", "an impersonal force"),
    (r"\bein engel\b|\bengel\b", "an angel"),
    (r"\bnur ein (?:mensch|prophet|lehrer)\b", "only a man"),
    (r"\bsondern\b|\baber\b", "but"),
    (r"\bund\b", "and"),
    (r"\bbetrachtet\b|\bangesehen\b", "considered"),
    (r"\barius lehrte\b|\barius behauptete\b", "Arius taught"),
    (r"\bmanche glauben\b|\beinige glauben\b", "some people believe"),
    (r"\bdass\b", "that"),
]

_TABLES = {lang: [(re.compile(p, re.I), r) for p, r in table] for lang, table in
           (("es", _ES), ("pt", _PT), ("de", _DE))}


def pivot(text: str, lang: str) -> str:
    """Rewrite the doctrinal core of `text` into English for the rules. Unknown language: unchanged."""
    table = _TABLES.get(lang)
    if not table:
        return text
    for rx, rep in table:
        text = rx.sub(rep, text)
    return text
