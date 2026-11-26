"""Doctrinal-consistency benchmark.

    python bench/run.py                 # writes results/benchmark.json and results/benchmark.md
    python bench/run.py --check         # fails if numbers differ from the committed results

Task: given a text, decide whether the speaker asserts something the Creed of 381
excludes ("contradicts") or not ("consistent" or "neutral"). The positive class is
"contradicts". Systems compared:

  keyword    a naive banned-phrase baseline (what most "guardrails" start as)
  symbolic   the pattern parser + rule checker alone
  neural     the hashed n-gram guard alone (block threshold from training)
  dual       the Dust layer: symbolic proofs, neural fallback gated by stance

The evaluation set is split deterministically into dev (for error analysis) and test
(reported). Overlap with the training data is measured and reported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dust.layer import Layer  # noqa: E402
from dust.neural import Guard  # noqa: E402

EVAL = ROOT / "data" / "eval" / "nicene-eval-v0.jsonl"
TRAIN = ROOT / "data" / "train.jsonl"
OUT_JSON = ROOT / "results" / "benchmark.json"
OUT_MD = ROOT / "results" / "benchmark.md"

KEYWORDS = re.compile(r"\b(created|creature|not god|only a man|just a man|myth|metaphor|force|modes?|did not rise|never rose|three gods|demiurge|not divine|prophet)\b", re.I)


def split(item_id: str) -> str:
    return "test" if int(hashlib.sha256(item_id.encode()).hexdigest(), 16) % 2 else "dev"


def keyword_predict(text: str) -> bool:
    return bool(KEYWORDS.search(text))


def metrics(pairs: list[tuple[bool, bool]]) -> dict:
    tp = sum(1 for g, p in pairs if g and p)
    fp = sum(1 for g, p in pairs if not g and p)
    fn = sum(1 for g, p in pairs if g and not p)
    tn = sum(1 for g, p in pairs if not g and not p)
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"n": len(pairs), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": round(prec, 3), "recall": round(rec, 3), "f1": round(f1, 3),
            "accuracy": round((tp + tn) / len(pairs), 3) if pairs else 0.0,
            "false_positive_rate": round(fp / (fp + tn), 3) if fp + tn else 0.0}


def ngrams(s: str, n: int = 4) -> set:
    w = re.findall(r"\w+", s.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}


def overlap_report(items: list[dict]) -> dict:
    train = [json.loads(line)["text"] for line in TRAIN.read_text(encoding="utf-8").splitlines()]
    train_set = {t.lower().strip() for t in train}
    train_grams = [ngrams(t) for t in train]
    exact = sum(1 for it in items if it["text"].lower().strip() in train_set)
    near = 0
    for it in items:
        g = ngrams(it["text"])
        if g and any(len(g & tg) / len(g | tg) >= 0.5 for tg in train_grams if tg):
            near += 1
    return {"exact_duplicates": exact, "near_duplicates_jaccard4_ge_0.5": near, "n_eval": len(items)}


def run() -> dict:
    items = [json.loads(line) for line in EVAL.read_text(encoding="utf-8").splitlines()]
    guard = Guard.load()
    systems = {
        "symbolic": Layer(mode="symbolic"),
        "neural": Layer(guard=guard, mode="neural"),
        "dual": Layer(guard=guard, mode="dual"),
    }
    preds: dict[str, dict[str, bool]] = defaultdict(dict)
    flagged: dict[str, bool] = {}
    lat: dict[str, list[float]] = defaultdict(list)
    for it in items:
        t0 = time.perf_counter()
        preds["keyword"][it["id"]] = keyword_predict(it["text"])
        lat["keyword"].append((time.perf_counter() - t0) * 1000)
        for name, layer in systems.items():
            t0 = time.perf_counter()
            v = layer.check(it["text"])
            lat[name].append((time.perf_counter() - t0) * 1000)
            preds[name][it["id"]] = v.decision == "block"
            if name == "dual":
                flagged[it["id"]] = v.decision in ("block", "flag")

    report: dict = {"eval_file": str(EVAL.relative_to(ROOT)), "eval_sha256": hashlib.sha256(EVAL.read_bytes()).hexdigest(),
                    "guard": guard.meta.get("name"), "thresholds": {"block": guard.meta.get("threshold_block"),
                                                                     "flag": guard.meta.get("threshold_flag")},
                    "splits": {}, "overlap_with_training": overlap_report(items)}
    for split_name in ("test", "dev", "all"):
        subset = [it for it in items if split_name == "all" or split(it["id"]) == split_name]
        block: dict = {"n": len(subset), "systems": {}}
        for name in ["keyword", "symbolic", "neural", "dual"]:
            pairs = [(it["label"] == "contradicts", preds[name][it["id"]]) for it in subset]
            sysrep = {"overall": metrics(pairs), "by_category": {}, "by_language": {}}
            for key, field in (("by_category", "category"), ("by_language", "lang")):
                groups = defaultdict(list)
                for it in subset:
                    groups[it[field]].append((it["label"] == "contradicts", preds[name][it["id"]]))
                sysrep[key] = {k: metrics(v) for k, v in sorted(groups.items())}
            block["systems"][name] = sysrep
        report["splits"][split_name] = block
    by_lang = defaultdict(list)
    for it in items:
        by_lang[it["lang"]].append((it["label"] == "contradicts", flagged[it["id"]]))
    report["dual_block_or_flag_by_language"] = {k: metrics(v) for k, v in sorted(by_lang.items())}
    report["latency_ms_per_item"] = {k: {"median": round(statistics.median(v), 3), "p95": round(sorted(v)[int(0.95 * len(v)) - 1], 3)}
                                     for k, v in lat.items()}
    report["errors_dual_all"] = [
        {"id": it["id"], "split": split(it["id"]), "category": it["category"], "lang": it["lang"], "label": it["label"],
         "predicted_block": preds["dual"][it["id"]], "text": it["text"]}
        for it in items if (it["label"] == "contradicts") != preds["dual"][it["id"]]]
    return report


def to_markdown(r: dict) -> str:
    L = ["# Benchmark results", "",
         f"Eval set `{r['eval_file']}` (sha256 `{r['eval_sha256'][:12]}`), guard `{r['guard']}`, "
         f"block threshold {r['thresholds']['block']}. Positive class: the text asserts something the Creed excludes.", "",
         "Latency is measured on the CI or sandbox CPU and excludes model generation. Numbers are regenerated by `python bench/run.py`.", ""]
    for split_name in ("test", "dev", "all"):
        b = r["splits"][split_name]
        L += [f"## {split_name} split (n={b['n']})", "", "| system | precision | recall | F1 | false-positive rate | accuracy |", "|---|---|---|---|---|---|"]
        for name, s in b["systems"].items():
            o = s["overall"]
            L.append(f"| {name} | {o['precision']:.3f} | {o['recall']:.3f} | {o['f1']:.3f} | {o['false_positive_rate']:.3f} | {o['accuracy']:.3f} |")
        L.append("")
        if split_name == "all":
            L += ["### Dust (dual) by category, all items", "", "| category | n | precision | recall | false-positive rate | accuracy |", "|---|---|---|---|---|---|"]
            for k, o in b["systems"]["dual"]["by_category"].items():
                L.append(f"| {k} | {o['n']} | {o['precision']:.3f} | {o['recall']:.3f} | {o['false_positive_rate']:.3f} | {o['accuracy']:.3f} |")
            L += ["", "### Dust (dual) by language, all items", "", "| language | n | precision | recall | false-positive rate | accuracy |", "|---|---|---|---|---|---|"]
            for k, o in b["systems"]["dual"]["by_language"].items():
                L.append(f"| {k} | {o['n']} | {o['precision']:.3f} | {o['recall']:.3f} | {o['false_positive_rate']:.3f} | {o['accuracy']:.3f} |")
            L.append("")
    L += ["## Dust (dual), counting a flag as a detection, by language", "",
          "Outside English, Spanish and Portuguese the guard is not allowed to block, only to flag. This table shows how many contradictions it would surface for human review.", "",
          "| language | n | precision | recall | false-positive rate |", "|---|---|---|---|---|"]
    for k, o in r["dual_block_or_flag_by_language"].items():
        L.append(f"| {k} | {o['n']} | {o['precision']:.3f} | {o['recall']:.3f} | {o['false_positive_rate']:.3f} |")
    L.append("")
    L += ["## Latency (ms per item, checking only)", "", "| system | median | p95 |", "|---|---|---|"]
    for k, v in r["latency_ms_per_item"].items():
        L.append(f"| {k} | {v['median']} | {v['p95']} |")
    o = r["overlap_with_training"]
    L += ["", "## Overlap with training data", "",
          f"{o['exact_duplicates']} exact and {o['near_duplicates_jaccard4_ge_0.5']} near duplicates (word 4-gram Jaccard >= 0.5) out of {o['n_eval']} eval items.", "",
          f"## Every error made by Dust (dual), all splits ({len(r['errors_dual_all'])})", "", "| id | split | category | lang | gold | blocked? | text |", "|---|---|---|---|---|---|---|"]
    for e in r["errors_dual_all"]:
        L.append(f"| {e['id']} | {e['split']} | {e['category']} | {e['lang']} | {e['label']} | {'yes' if e['predicted_block'] else 'no'} | {e['text']} |")
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if metrics differ from committed results")
    ap.add_argument("--out", default=str(OUT_JSON))
    args = ap.parse_args()
    r = run()
    if args.check:
        old = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        for split_name in ("test", "dev", "all"):
            for name in ("keyword", "symbolic", "neural", "dual"):
                a = old["splits"][split_name]["systems"][name]["overall"]
                b = r["splits"][split_name]["systems"][name]["overall"]
                if {k: a[k] for k in ("tp", "fp", "fn", "tn")} != {k: b[k] for k in ("tp", "fp", "fn", "tn")}:
                    raise SystemExit(f"benchmark drift in {split_name}/{name}: {a} != {b}")
        print("benchmark reproduces committed results")
        return
    stable = {k: v for k, v in r.items() if k != "latency_ms_per_item"}
    Path(args.out).write_text(json.dumps({**stable, "latency_ms_per_item": r["latency_ms_per_item"]}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(to_markdown(r), encoding="utf-8")
    t = r["splits"]["test"]["systems"]
    for name, s in t.items():
        print(f"test {name:8s} P={s['overall']['precision']:.3f} R={s['overall']['recall']:.3f} F1={s['overall']['f1']:.3f} FPR={s['overall']['false_positive_rate']:.3f}")


if __name__ == "__main__":
    main()
