"""Tiny offline retriever over the Creed's propositions (BM25 over a few hundred words).

It answers one question: which articles of the Creed does this user question touch?
The selected articles and their Scripture are placed in the system prompt, so a small
model sees the exact boundary that applies instead of only the whole Creed.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from .kb import KnowledgeBase

_TOK = re.compile(r"[a-z]+")
_STOP = set("the a an of and or to in is was are be by for with that this it on as at from who whom what which not his he him".split())

# Extra cue words per group, so everyday questions find the right article.
_CUES = {
    "one-god": "god creator maker world creation matter universe demiurge gods polytheism",
    "trinity": "trinity three persons modes modalism roles father son spirit oneness distinct",
    "son-eternal": "eternal created creature begotten beginning arius arian angel michael time existed adopted",
    "son-divine": "divine deity god man prophet teacher human homoousios substance equal lesser",
    "creation-through-son": "creation made through word logos",
    "incarnation": "incarnation flesh human body virgin mary birth born conceived docetism seemed",
    "crucifixion": "cross crucified died death pilate suffered buried swoon",
    "resurrection": "resurrection rose risen tomb empty third day metaphor body raised",
    "ascension": "ascension ascended heaven right hand",
    "return-judgement": "return second coming judge judgement judgment kingdom end",
    "holy-spirit": "spirit ghost force person proceeds filioque worship lord giver life prophets",
    "church": "church catholic apostolic",
    "baptism": "baptism baptise baptize forgiveness sins",
    "resurrection-dead": "afterlife resurrection dead death heaven world come eternal life",
}


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 4 and t.endswith("s") and not t.endswith("ss") else t


def _toks(s: str) -> list[str]:
    return [_stem(t) for t in _TOK.findall(s.lower()) if t not in _STOP]


def rank(kb: KnowledgeBase, query: str, k: int = 3):
    docs = []
    for p in kb.propositions:
        errs = " ".join(e.name + " " + e.summary for e in kb.errors if p.id in e.contradicts)
        docs.append((p, _toks(p.text + " " + errs + " " + _CUES.get(p.group, ""))))
    n = len(docs)
    avg = sum(len(d) for _, d in docs) / n
    df = Counter(t for _, d in docs for t in set(d))
    q = _toks(query)
    scored = []
    for p, d in docs:
        tf = Counter(d)
        s = 0.0
        for t in q:
            if t in tf:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * tf[t] * 2.2 / (tf[t] + 1.2 * (0.25 + 0.75 * len(d) / avg))
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: -x[0])
    return [p for _, p in scored[:k]]
