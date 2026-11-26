"""End-to-end evaluation against a real model behind an OpenAI-compatible endpoint.

    python bench/e2e.py --backend http://localhost:11434/v1 --model qwen2.5:3b-instruct

For each question in data/eval/questions-v0.jsonl it asks the model twice: raw (the
model's own alignment only) and through Dust (constitution + retrieval + check +
repair). It reports how often the final answer is blocked by the checker, how often Dust
had to repair or refuse, and writes every transcript to results/e2e-<model>.jsonl for
people to read. The checker is not an oracle: read the transcripts.

First run: 2026-11-26 on a Windows desktop (Ryzen 5 5600G, GTX 1650 SUPER 4 GB, 7.4 GB RAM)
with qwen2.5 1.5B and 3B instruct through Ollama. See docs/findings.md.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dust import Layer  # noqa: E402
from dust.backends import OpenAICompatible  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--tag", default="", help="suffix for the output files, e.g. run2")
    ap.add_argument("--questions", default="data/eval/questions-v0.jsonl", help="question file (JSONL with id, question)")
    args = ap.parse_args()
    qs = [json.loads(line) for line in (ROOT / args.questions).read_text(encoding="utf-8").splitlines()]
    backend = OpenAICompatible(args.backend, args.model)
    layer = Layer()
    aligned = layer.wrap(backend)
    name = args.model.replace("/", "_").replace(":", "_") + (f"-{args.tag}" if args.tag else "")
    out = ROOT / "results" / f"e2e-{name}.jsonl"
    stats = {"n": 0, "raw": {"pass": 0, "flag": 0, "block": 0}, "dust_final": {"pass": 0, "flag": 0, "block": 0},
             "dust_repaired": 0, "dust_refused": 0, "dust_flagged_by_guard_only": 0, "seconds": 0.0}
    t_all = time.time()
    with out.open("w", encoding="utf-8") as fh:
        for q in qs:
            msgs = [{"role": "user", "content": q["question"]}]
            t0 = time.time()
            raw = backend.generate(msgs)
            raw_v = layer.check(raw)
            r = aligned.chat(msgs)
            stats["n"] += 1
            stats["raw"][raw_v.decision] += 1
            stats["dust_final"][r.verdict.decision] += 1
            stats["dust_repaired"] += r.repaired
            stats["dust_refused"] += r.refused
            stats["dust_flagged_by_guard_only"] += any(f.source == "neural" for f in r.verdict.flags) and not r.refused
            hits = lambda v: [{"p": x.proposition, "src": x.source, "sentence": x.sentence} for x in v.violations + v.flags]
            fh.write(json.dumps({
                "id": q["id"], "question": q["question"],
                "raw": raw, "raw_decision": raw_v.decision, "raw_hits": hits(raw_v),
                "dust": r.content, "dust_decision": r.verdict.decision, "attempts": r.attempts,
                "repaired": r.repaired, "refused": r.refused,
                "drafts": [{"text": d, "decision": v.decision, "hits": hits(v)} for d, v in zip(r.drafts, r.draft_verdicts)],
                "seconds": round(time.time() - t0, 1)}, ensure_ascii=False) + "\n")
    stats["seconds"] = round(time.time() - t_all, 1)
    print(json.dumps(stats, indent=1))
    print(f"transcripts: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
