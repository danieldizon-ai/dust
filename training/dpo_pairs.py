"""Build preference pairs for DPO from the Creed knowledge base.

    python training/dpo_pairs.py > data/dpo_pairs.jsonl

Each pair is {"prompt", "chosen", "rejected", "proposition", "error"}: a study question,
an answer that affirms the article (with Scripture from the bundled public-domain WEB)
and an answer that asserts the excluded error. This is a seed set for the recipe in
lora_dpo.py, not a finished dataset: real preference data should be written or reviewed
by people from more than one tradition (see docs/methods.md).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from dust.kb import load  # noqa: E402

PROMPTS = [
    "What does the Nicene Creed teach about this: {topic}?",
    "A student asks: is this Christian teaching? \"{summary}\"",
    "Explain briefly whether Christians can hold that {summary_lc}",
]


def build() -> list[dict]:
    kb = load()
    pairs = []
    for e in kb.errors:
        pid = e.contradicts[0]
        p = kb.proposition(pid)
        ref, verse = kb.verses(pid)[0]
        chosen = (f"The Creed of 381 confesses: {p.text} This answers the view known as {e.name}, which held that "
                  f"{e.summary[0].lower() + e.summary[1:]} The Church rejected that view ({e.condemned}). "
                  f"See {ref}: \"{verse}\"")
        rejected = f"{e.summary} That is the most reasonable reading, and Christians are free to believe it."
        for tmpl in PROMPTS:
            pairs.append({"prompt": tmpl.format(topic=e.name, summary=e.summary,
                                                summary_lc=e.summary[0].lower() + e.summary[1:]),
                          "chosen": chosen, "rejected": rejected, "proposition": pid, "error": e.id})
    return pairs


if __name__ == "__main__":
    for row in build():
        print(json.dumps(row, ensure_ascii=False))
