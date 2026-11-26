"""End-to-end evaluation against a real model behind an OpenAI-compatible endpoint.

    python bench/e2e.py --backend http://localhost:11434/v1 --model qwen2.5:3b-instruct

For each question in data/eval/questions-v0.jsonl it asks the model twice: raw (the
model's own alignment only) and through Dust (constitution + retrieval + check +
repair). It reports how often the final answer is blocked by the checker, how often Dust
had to repair or refuse, and writes every transcript to results/e2e-<model>.jsonl for
people to read. The checker is not an oracle: read the transcripts.

Not run for v0.1: the sandbox that built it could not download model weights.
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
    args = ap.parse_args()
    qs = [json.loads(line) for line in (ROOT / "data/eval/questions-v0.jsonl").read_text(encoding="utf-8").splitlines()]
    backend = OpenAICompatible(args.backend, args.model)
    layer = Layer()
    aligned = layer.wrap(backend)
    out = ROOT / "results" / f"e2e-{args.model.replace('/', '_').replace(':', '_')}.jsonl"
    stats = {"n": 0, "raw_blocked": 0, "dust_repaired": 0, "dust_refused": 0, "dust_blocked_final": 0}
    with out.open("w", encoding="utf-8") as fh:
        for q in qs:
            msgs = [{"role": "user", "content": q["question"]}]
            t0 = time.time()
            raw = backend.generate(msgs)
            raw_v = layer.check(raw)
            r = aligned.chat(msgs)
            stats["n"] += 1
            stats["raw_blocked"] += raw_v.decision == "block"
            stats["dust_repaired"] += r.repaired
            stats["dust_refused"] += r.refused
            fh.write(json.dumps({"id": q["id"], "question": q["question"], "raw": raw, "raw_decision": raw_v.decision,
                                 "dust": r.content, "dust_decision": r.verdict.decision, "attempts": r.attempts,
                                 "seconds": round(time.time() - t0, 1)}, ensure_ascii=False) + "\n")
    print(json.dumps(stats, indent=1))
    print(f"transcripts: {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
