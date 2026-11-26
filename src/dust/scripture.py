"""Scripture reference checking: find Bible references in text, check that they exist,
and (optionally, with a full Bible text) check that quotations match.

Models invent references and misquote verses. A study tool should never show a
reference that does not exist. This module is the mechanical part of "Scripture is
looked up, never recalled": existence checks need only versification (bundled, 6 KB);
quotation checks need verse text (pass a web-bible-rag style verses.jsonl).
"""
from __future__ import annotations

import difflib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources

# Common names and abbreviations (English). Keys are lower-case, without trailing dots.
_ALIASES = {
    "gen": "Genesis", "ge": "Genesis", "gn": "Genesis", "exod": "Exodus", "ex": "Exodus", "exo": "Exodus",
    "lev": "Leviticus", "lv": "Leviticus", "num": "Numbers", "nm": "Numbers", "deut": "Deuteronomy", "dt": "Deuteronomy",
    "josh": "Joshua", "jos": "Joshua", "judg": "Judges", "jdg": "Judges", "ru": "Ruth", "rth": "Ruth",
    "1 sam": "1 Samuel", "2 sam": "2 Samuel", "1 kgs": "1 Kings", "2 kgs": "2 Kings", "1 ki": "1 Kings", "2 ki": "2 Kings",
    "1 chr": "1 Chronicles", "2 chr": "2 Chronicles", "1 chron": "1 Chronicles", "2 chron": "2 Chronicles",
    "neh": "Nehemiah", "esth": "Esther", "est": "Esther", "jb": "Job", "ps": "Psalms", "psa": "Psalms", "psalm": "Psalms",
    "pss": "Psalms", "prov": "Proverbs", "pr": "Proverbs", "prv": "Proverbs", "eccl": "Ecclesiastes", "ecc": "Ecclesiastes",
    "qoh": "Ecclesiastes", "song": "Song of Solomon", "song of songs": "Song of Solomon", "sos": "Song of Solomon",
    "canticles": "Song of Solomon", "isa": "Isaiah", "is": "Isaiah", "jer": "Jeremiah", "lam": "Lamentations",
    "ezek": "Ezekiel", "eze": "Ezekiel", "dan": "Daniel", "dn": "Daniel", "hos": "Hosea", "joe": "Joel", "jl": "Joel",
    "am": "Amos", "obad": "Obadiah", "ob": "Obadiah", "jon": "Jonah", "mic": "Micah", "nah": "Nahum", "hab": "Habakkuk",
    "zeph": "Zephaniah", "zep": "Zephaniah", "hag": "Haggai", "zech": "Zechariah", "zec": "Zechariah", "mal": "Malachi",
    "matt": "Matthew", "mt": "Matthew", "mk": "Mark", "mrk": "Mark", "lk": "Luke", "luk": "Luke", "jn": "John", "jhn": "John",
    "acts of the apostles": "Acts", "act": "Acts", "rom": "Romans", "rm": "Romans", "1 cor": "1 Corinthians",
    "2 cor": "2 Corinthians", "gal": "Galatians", "eph": "Ephesians", "phil": "Philippians", "php": "Philippians",
    "col": "Colossians", "1 thess": "1 Thessalonians", "2 thess": "2 Thessalonians", "1 thes": "1 Thessalonians",
    "2 thes": "2 Thessalonians", "1 tim": "1 Timothy", "2 tim": "2 Timothy", "tit": "Titus", "philem": "Philemon",
    "phlm": "Philemon", "heb": "Hebrews", "jas": "James", "jm": "James", "1 pet": "1 Peter", "2 pet": "2 Peter",
    "1 pt": "1 Peter", "2 pt": "2 Peter", "1 jn": "1 John", "2 jn": "2 John", "3 jn": "3 John", "jud": "Jude",
    "rev": "Revelation", "revelations": "Revelation", "apocalypse": "Revelation",
}
_ORDINALS = {"i": "1", "ii": "2", "iii": "3", "first": "1", "second": "2", "third": "3"}


@dataclass
class Reference:
    text: str          # as written
    book: str | None   # canonical name, None if unknown
    chapter: int
    verse_start: int | None
    verse_end: int | None
    exists: bool
    problem: str = ""  # why it does not exist
    quote: str | None = None
    quote_similarity: float | None = None

    @property
    def canonical(self) -> str:
        if not self.book:
            return self.text
        v = "" if self.verse_start is None else f":{self.verse_start}" + (f"-{self.verse_end}" if self.verse_end and self.verse_end != self.verse_start else "")
        return f"{self.book} {self.chapter}{v}"


@lru_cache(maxsize=1)
def _versification() -> dict[str, list[int]]:
    data = json.loads(resources.files("dust.data").joinpath("versification.json").read_text(encoding="utf-8"))
    return {b["name"]: b["verses"] for b in data["books"]}


@lru_cache(maxsize=1)
def _book_lookup() -> dict[str, str]:
    look = {name.lower(): name for name in _versification()}
    look.update(_ALIASES)
    return look


def _book_regex() -> re.Pattern:
    keys = set(_book_lookup())
    keys |= {k[2:] for k in keys if k[:2] in ("1 ", "2 ", "3 ")}
    names = sorted(keys, key=len, reverse=True)
    alt = "|".join(re.escape(n).replace(r"\ ", r"\s*") for n in names)
    prefix = r"(?:(?P<ord>[123]|i{1,3}|first|second|third)\s+)?"
    return re.compile(r"\b" + prefix + r"(?P<book>" + alt + r")\.?\s+(?P<ch>\d{1,3})(?:\s*[:.]\s*(?P<v1>\d{1,3})(?:\s*[-–]\s*(?P<v2>\d{1,3}))?)?\b", re.I)


_REF_RX = None


def find(text: str) -> list[Reference]:
    global _REF_RX
    if _REF_RX is None:
        _REF_RX = _book_regex()
    look = _book_lookup()
    versif = _versification()
    out = []
    for m in _REF_RX.finditer(text):
        key = re.sub(r"\s+", " ", m.group("book").lower())
        if m.group("ord"):
            key = _ORDINALS.get(m.group("ord").lower(), m.group("ord")) + " " + key
        book = look.get(key)
        if book is None and m.group("ord") is None:
            continue
        ch = int(m.group("ch"))
        v1 = int(m.group("v1")) if m.group("v1") else None
        v2 = int(m.group("v2")) if m.group("v2") else None
        ref = Reference(m.group(0), book, ch, v1, v2, True)
        if book is None:
            ref.exists, ref.problem = False, "unknown book"
        elif ch < 1 or ch > len(versif[book]):
            ref.exists, ref.problem = False, f"{book} has {len(versif[book])} chapters"
        elif v1 is not None and (v1 < 1 or v1 > versif[book][ch - 1]):
            ref.exists, ref.problem = False, f"{book} {ch} has {versif[book][ch - 1]} verses"
        elif v2 is not None and (v2 < (v1 or 1) or v2 > versif[book][ch - 1]):
            ref.exists, ref.problem = False, f"{book} {ch} has {versif[book][ch - 1]} verses"
        out.append(ref)
    return out


class Bible:
    """Verse text for quotation checks. Load a web-bible-rag style verses.jsonl
    (one JSON object per verse with "book", "chapter", "verse", "text")."""

    def __init__(self, verses: dict[tuple[str, int, int], str], name: str = ""):
        self.verses = verses
        self.name = name

    @classmethod
    def from_jsonl(cls, path: str, name: str = "WEB") -> "Bible":
        verses = {}
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                r = json.loads(line)
                verses[(r["book"], int(r["chapter"]), int(r["verse"]))] = r["text"]
        return cls(verses, name)

    def passage(self, ref: Reference) -> str:
        if not ref.book or ref.verse_start is None:
            return ""
        end = ref.verse_end or ref.verse_start
        return " ".join(self.verses.get((ref.book, ref.chapter, v), "") for v in range(ref.verse_start, end + 1)).strip()


_QUOTE = re.compile(r"[\"“]([^\"”]{12,400})[\"”]")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", s.lower().replace("’", "'"))).strip()


def check_quotes(text: str, bible: Bible, refs: list[Reference] | None = None) -> list[Reference]:
    """Attach the nearest following or preceding quotation to each reference and score it
    against the verse text (difflib ratio on normalised text; 1.0 = exact)."""
    refs = refs if refs is not None else find(text)
    quotes = [(m.start(), m.group(1)) for m in _QUOTE.finditer(text)]
    for ref in refs:
        if not ref.exists or ref.verse_start is None or not quotes:
            continue
        pos = text.find(ref.text)
        q = min(quotes, key=lambda x: abs(x[0] - pos))
        if abs(q[0] - pos) > 300:
            continue
        verse = bible.passage(ref)
        if not verse:
            continue
        a, b = _norm(q[1]), _norm(verse)
        # a quotation may be part of a verse: compare against the best-matching window
        if len(a) < len(b):
            sm = difflib.SequenceMatcher(None, b, a, autojunk=False)
            blk = sm.find_longest_match(0, len(b), 0, len(a))
            start = max(0, blk.a - blk.b)
            b = b[start:start + len(a)]
        ref.quote = q[1]
        ref.quote_similarity = round(difflib.SequenceMatcher(None, a, b, autojunk=False).ratio(), 3)
    return refs
