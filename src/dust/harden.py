"""Input hardening: undo cheap tricks that hide a claim from the checker.

Text from a model (or a user trying to get something past a filter) can carry invisible
characters, compatibility forms and look-alike letters from other scripts. "Jеsus" with a
Cyrillic "е" reads the same to a person and is a different word to a regex. ``sanitize``
puts such text back into a canonical form before checking. It is conservative: it only
maps look-alike letters inside words that already mix Latin with another script, so Greek
and Cyrillic text (the Creed itself, Russian or Greek users) is left alone.
"""
from __future__ import annotations

import re
import unicodedata

# zero-width, joiners, soft hyphen, bidi controls, word joiner, BOM
_INVISIBLE = re.compile("[­᠎​-‏‪-‮⁠-⁤⁦-⁩﻿]")

# Cyrillic and Greek letters that are visually identical to Latin ones
_CONFUSABLES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
    "ѕ": "s", "һ": "h", "ԁ": "d", "ԛ": "q", "ԝ": "w",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C",
    "Т": "T", "Х": "X", "І": "I", "Ј": "J", "Ѕ": "S",
    "ο": "o", "α": "a", "ι": "i", "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "κ": "k",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N",
    "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})
_WORD = re.compile(r"\w+", re.UNICODE)
_LATIN = re.compile(r"[A-Za-z]")
_NONLATIN = re.compile(r"[Ͱ-ϿЀ-ӿԀ-ԯ]")


def _fix_word(m: re.Match) -> str:
    w = m.group(0)
    if _LATIN.search(w) and _NONLATIN.search(w):
        return w.translate(_CONFUSABLES)
    return w


def sanitize(text: str) -> str:
    """Canonical form for checking: NFKC, no invisible characters, no mixed-script words,
    letters spaced out with dots or hyphens ("J.e.s.u.s") rejoined."""
    t = unicodedata.normalize("NFKC", text)
    t = _INVISIBLE.sub("", t)
    t = _WORD.sub(_fix_word, t)
    # "c-r-e-a-t-e-d", "c.r.e.a.t.e.d" -> "created" (four or more single letters)
    t = re.sub(r"\b(?:[A-Za-z][.\-_*](?=[A-Za-z]\b)){3,}[A-Za-z]\b",
               lambda m: re.sub(r"[.\-_*]", "", m.group(0)), t)
    return t


def was_obfuscated(original: str, cleaned: str) -> bool:
    """True when sanitizing changed more than NFKC alone would (a sign of evasion)."""
    return unicodedata.normalize("NFKC", original) != cleaned
