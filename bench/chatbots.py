"""Dust 381 chatbot benchmark: how often do chatbots answer outside the Nicene Creed of 381?

Asks every question in a question file to every target, with no system prompt (the
model's own behaviour), screens each answer with the Dust checker, and builds a human
review queue. Only human-confirmed judgements go into the published score; the checker's
screen is reported beside it so readers can see how far automatic checking agrees.

    python bench/chatbots.py ask    --targets bench/targets.example.json --run 2027-02
    python bench/chatbots.py queue  --run 2027-02          # writes review.csv to fill in
    python bench/chatbots.py score  --run 2027-02          # scorecard.md from review.csv

Targets are any OpenAI-compatible endpoint (OpenAI, Google's and Anthropic's compatible
endpoints, Mistral, OpenRouter, a local Ollama). Keys come from environment variables
named in the targets file and are never written to disk. `ask` resumes: answers already
saved are skipped, so an interrupted run costs nothing twice.

Review file (review.csv) columns: target, id, lang, category, screen, human, note
  human = outside | inside | unclear   (outside = asserts, in its own voice or as what
  Christians believe, a position the Creed of 381 excludes; or says the Creed settles an
  open question)
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from dust import Layer  # noqa: E402
from dust.audit import fingerprint  # noqa: E402
from dust.backends import OpenAICompatible  # noqa: E402

OUT_ROOT = ROOT / "results" / "chatbots"

SAMPLE_PASSES = 0.2      # share of screened-pass answers also read by a human
SEED = 381


def load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_dir(run: str) -> Path:
    d = OUT_ROOT / run
    d.mkdir(parents=True, exist_ok=True)
    return d


def make_backend(t: dict):
    key = os.environ.get(t["api_key_env"]) if t.get("api_key_env") else None
    if t.get("api_key_env") and not key:
        raise SystemExit(f"{t['name']}: environment variable {t['api_key_env']} is not set")
    return OpenAICompatible(t["base_url"], t["model"], api_key=key, timeout=t.get("timeout", 180),
                            temperature=t.get("temperature", 0.7), max_tokens=t.get("max_tokens", 900))


def ask(targets: list[dict], questions: list[dict], run: str, backend_factory=make_backend, layer=None,
        pause: float = 0.0) -> None:
    layer = layer or Layer()
    d = run_dir(run)
    (d / "questions.jsonl").write_text("".join(json.dumps(q, ensure_ascii=False) + "\n" for q in questions),
                                       encoding="utf-8")
    meta = {"run": run, "targets": [{k: v for k, v in t.items() if k != "api_key_env"} for t in targets],
            "n_questions": len(questions), "boundary_fingerprint": fingerprint(layer.kb)}
    (d / "meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    for t in targets:
        out = d / f"answers-{t['name']}.jsonl"
        done = {r["id"] for r in load_jsonl(out)} if out.exists() else set()
        backend = backend_factory(t)
        with out.open("a", encoding="utf-8") as fh:
            for q in questions:
                if q["id"] in done:
                    continue
                t0 = time.time()
                try:
                    answer, error = backend.generate([{"role": "user", "content": q["question"]}]), None
                except Exception as e:  # keep going; the error is recorded and the item retried next time
                    print(f"{t['name']} {q['id']}: {e}", file=sys.stderr)
                    continue
                v = layer.check(answer)
                fh.write(json.dumps({
                    "target": t["name"], "id": q["id"], "lang": q.get("lang", "en"), "category": q.get("category", ""),
                    "question": q["question"], "answer": answer, "screen": v.decision,
                    "hits": [[x.proposition, x.source, x.sentence[:200]] for x in v.violations + v.flags],
                    "seconds": round(time.time() - t0, 2), "error": error}, ensure_ascii=False) + "\n")
                fh.flush()
                if pause:
                    time.sleep(pause)


def queue(run: str) -> Path:
    """Every screened block or flag, plus a fixed random share of passes, for human reading."""
    d = run_dir(run)
    rng = random.Random(SEED)
    rows = []
    for f in sorted(d.glob("answers-*.jsonl")):
        for r in load_jsonl(f):
            if r["screen"] != "pass" or rng.random() < SAMPLE_PASSES:
                rows.append(r)
    path = d / "review.csv"
    old = {}
    if path.exists():
        with path.open(encoding="utf-8", newline="") as fh:
            old = {(x["target"], x["id"]): x for x in csv.DictReader(fh)}
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, ["target", "id", "lang", "category", "screen", "human", "note", "question", "answer"])
        w.writeheader()
        for r in rows:
            prev = old.get((r["target"], r["id"]), {})
            w.writerow({"target": r["target"], "id": r["id"], "lang": r["lang"], "category": r["category"],
                        "screen": r["screen"], "human": prev.get("human", ""), "note": prev.get("note", ""),
                        "question": r["question"], "answer": r["answer"]})
    return path


def score(run: str) -> dict:
    d = run_dir(run)
    answers = {(r["target"], r["id"]): r for f in sorted(d.glob("answers-*.jsonl")) for r in load_jsonl(f)}
    human: dict[tuple[str, str], str] = {}
    if (d / "review.csv").exists():
        with (d / "review.csv").open(encoding="utf-8", newline="") as fh:
            for x in csv.DictReader(fh):
                if x.get("human") in ("outside", "inside", "unclear"):
                    human[(x["target"], x["id"])] = x["human"]
    by_target: dict[str, dict] = defaultdict(lambda: {"n": 0, "screen": Counter(), "reviewed": 0, "outside": 0,
                                                     "unclear": 0, "pending": 0, "by_lang": defaultdict(Counter)})
    for key, r in answers.items():
        s = by_target[r["target"]]
        s["n"] += 1
        s["screen"][r["screen"]] += 1
        h = human.get(key)
        needs_review = r["screen"] != "pass"
        if h:
            s["reviewed"] += 1
            s["outside"] += h == "outside"
            s["unclear"] += h == "unclear"
            s["by_lang"][r["lang"]]["outside" if h == "outside" else "ok"] += 1
        elif needs_review:
            s["pending"] += 1
    # Answers screened pass and not sampled count as inside; the sampled passes estimate
    # how many outside answers the screen misses, reported separately (screen_miss_rate).
    report = {}
    for name, s in sorted(by_target.items()):
        sampled_pass = [k for k, r in answers.items() if r["target"] == name and r["screen"] == "pass" and k in human]
        missed = sum(human[k] == "outside" for k in sampled_pass)
        report[name] = {
            "answers": s["n"], "outside_confirmed": s["outside"], "unclear": s["unclear"],
            "outside_per_100": round(100 * s["outside"] / s["n"], 1) if s["n"] else None,
            "screen": dict(s["screen"]), "awaiting_review": s["pending"],
            "screen_miss_rate_in_sample": round(missed / len(sampled_pass), 3) if sampled_pass else None,
            "by_lang": {k: dict(v) for k, v in s["by_lang"].items()}}
    (d / "scorecard.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    lines = [f"# Dust 381 chatbot benchmark: {run}", "",
             "Answers that assert a position the Nicene Creed of 381 excludes, or claim the Creed settles an open "
             "question, confirmed by human review. The checker's screen is shown for comparison.", "",
             "| Target | Answers | Outside the boundary (confirmed) | Per 100 | Unclear | Awaiting review | Screen: block / flag / pass | Screen misses in sampled passes |",
             "|---|---|---|---|---|---|---|---|"]
    for name, r in report.items():
        sc = r["screen"]
        miss = "n/a" if r["screen_miss_rate_in_sample"] is None else f"{100 * r['screen_miss_rate_in_sample']:.0f}%"
        lines.append(f"| {name} | {r['answers']} | {r['outside_confirmed']} | {r['outside_per_100']} | {r['unclear']} | "
                     f"{r['awaiting_review']} | {sc.get('block', 0)} / {sc.get('flag', 0)} / {sc.get('pass', 0)} | {miss} |")
    if any(r["awaiting_review"] for r in report.values()):
        lines += ["", "**Not publishable yet:** some screened answers have not been reviewed."]
    (d / "scorecard.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["ask", "queue", "score"])
    ap.add_argument("--run", required=True, help="run name, e.g. 2027-02")
    ap.add_argument("--targets", default="bench/targets.example.json")
    ap.add_argument("--questions", default="data/eval/questions-v1.jsonl")
    ap.add_argument("--only", action="append", default=[], help="target name(s) to run")
    ap.add_argument("--limit", type=int, default=0, help="first N questions only (smoke test)")
    ap.add_argument("--pause", type=float, default=0.0, help="seconds between calls")
    a = ap.parse_args()
    if a.command == "ask":
        targets = json.loads((ROOT / a.targets).read_text(encoding="utf-8"))
        if a.only:
            targets = [t for t in targets if t["name"] in a.only]
        qs = load_jsonl(ROOT / a.questions)
        if a.limit:
            qs = qs[:a.limit]
        ask(targets, qs, a.run, pause=a.pause)
    elif a.command == "queue":
        print(queue(a.run))
    else:
        print(json.dumps(score(a.run), indent=1))


if __name__ == "__main__":
    main()
