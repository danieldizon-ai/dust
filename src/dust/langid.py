"""Crude stop-word language identification, enough to know when the guard is outside
the languages it was trained on. Not a general-purpose language identifier."""
from __future__ import annotations

import re

_STOP = {
    "en": "the is was are were be been and of not to a an that this it they we he his in on will did does do has have there no never god jesus christ son spirit only just".split(),
    "es": "el la los las es fue y de no que un una solo dios jesús hijo espíritu cristo".split(),
    "pt": "o a os as é foi e de não que um uma apenas deus jesus filho espírito cristo".split(),
    "fr": "le la les est était et de ne pas que un une seulement dieu jésus fils esprit christ".split(),
    "de": "der die das ist war und von nicht dass ein eine nur gott jesus sohn geist christus".split(),
    "tl": "ang ng si ay hindi na sa mga lamang diyos hesus anak espiritu kristo".split(),
    "id": "yang dan adalah bukan dari itu ini hanya allah yesus anak roh kristus".split(),
}
_W = re.compile(r"[\w']+", re.UNICODE)


def detect(text: str) -> str:
    words = [w.lower() for w in _W.findall(text)]
    if not words:
        return "unknown"
    best, score = "unknown", 0
    for lang, stops in _STOP.items():
        s = sum(1 for w in words if w in stops)
        if s > score:
            best, score = lang, s
    return best if score >= 2 or (score >= 1 and len(words) <= 4) else "unknown"
