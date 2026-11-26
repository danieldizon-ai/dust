"""Build the Hugging Face dataset folder `hf/dust-nicene-381/` from the repo.

    python hf/build_dataset.py

Daniel uploads the folder himself (huggingface-cli upload danieldizon/dust-nicene-381
hf/dust-nicene-381 --repo-type dataset). Nothing here talks to the network.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
from run import split  # noqa: E402  same deterministic dev/test split as the benchmark

OUT = ROOT / "hf" / "dust-nicene-381"


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    items = [json.loads(l) for l in (ROOT / "data/eval/nicene-eval-v0.jsonl").read_text(encoding="utf-8").splitlines()]
    for it in items:
        it["split"] = split(it["id"])
    write_jsonl(OUT / "claims/test.jsonl", [i for i in items if i["split"] == "test"])
    write_jsonl(OUT / "claims/dev.jsonl", [i for i in items if i["split"] == "dev"])
    qs = [json.loads(l) for l in (ROOT / "data/eval/questions-v0.jsonl").read_text(encoding="utf-8").splitlines()]
    write_jsonl(OUT / "questions/v0.jsonl", qs)
    kb = json.loads((ROOT / "src/dust/data/creed.json").read_text(encoding="utf-8"))
    write_jsonl(OUT / "boundary/propositions.jsonl", kb["propositions"])
    write_jsonl(OUT / "boundary/excluded_errors.jsonl", kb["excluded_errors"])
    write_jsonl(OUT / "boundary/latitude.jsonl", kb["latitude"])
    (OUT / "boundary/creed-381.json").write_text(json.dumps(
        {k: kb[k] for k in ("id", "title", "version", "attribution", "texts")}, ensure_ascii=False, indent=1),
        encoding="utf-8", newline="\n")
    prof = []
    for p in sorted((ROOT / "src/dust/data/extensions").glob("*.json")):
        prof.append(json.loads(p.read_text(encoding="utf-8")))
    write_jsonl(OUT / "profiles/profiles.jsonl", prof)
    card = (ROOT / "hf/README.template.md").read_text(encoding="utf-8")
    n_test = sum(i["split"] == "test" for i in items)
    card = card.replace("{N_TEST}", str(n_test)).replace("{N_DEV}", str(len(items) - n_test)).replace(
        "{N_PROPS}", str(len(kb["propositions"]))).replace("{N_ERRORS}", str(len(kb["excluded_errors"]))).replace(
        "{N_LAT}", str(len(kb["latitude"]))).replace("{N_PROFILES}", str(len(prof)))
    (OUT / "README.md").write_text(card, encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
