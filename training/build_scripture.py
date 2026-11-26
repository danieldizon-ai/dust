"""Build src/dust/data/scripture.json: the World English Bible (public domain) text of
every verse referenced by the Creed propositions.

Usage: python training/build_scripture.py PATH/TO/verses.jsonl

The input is the verses file of the web-bible-rag dataset (CC0), one JSON object per
verse with a "reference" field such as "John 1:14".
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREED = ROOT / "src/dust/data/creed.json"
OUT = ROOT / "src/dust/data/scripture.json"


def main(path: str) -> None:
    creed = json.loads(CREED.read_text())
    wanted = {ref for p in creed["propositions"] for ref in p["scripture"]}
    found = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            row = json.loads(line)
            if row["reference"] in wanted:
                found[row["reference"]] = row["text"]
    missing = sorted(wanted - set(found))
    if missing:
        raise SystemExit(f"missing verses: {missing}")
    OUT.write_text(json.dumps({
        "translation": "World English Bible (WEB)",
        "licence": "Public domain",
        "verses": dict(sorted(found.items())),
    }, ensure_ascii=False, indent=1) + "\n")
    print(f"wrote {len(found)} verses to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1])
