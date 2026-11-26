import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "bench"))
import chatbots  # noqa: E402
from dust import Layer  # noqa: E402
from dust.backends import Scripted  # noqa: E402


def test_ask_queue_score_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(chatbots, "OUT_ROOT", tmp_path)
    qs = [{"id": "a", "lang": "en", "category": "core", "question": "Was Jesus created?"},
          {"id": "b", "lang": "en", "category": "core", "question": "Did he rise?"}]
    replies = {"bot1": ["Yes, Jesus was created by God.", "Yes, he rose bodily from the dead."]}
    factory = lambda t: Scripted(replies[t["name"]])  # noqa: E731
    lay = Layer(mode="symbolic")
    chatbots.ask([{"name": "bot1"}], qs, "t", backend_factory=factory, layer=lay)
    chatbots.ask([{"name": "bot1"}], qs, "t", backend_factory=factory, layer=lay)  # resumes: nothing asked twice
    answers = chatbots.load_jsonl(tmp_path / "t" / "answers-bot1.jsonl")
    assert [r["id"] for r in answers] == ["a", "b"] and answers[0]["screen"] == "block"
    path = chatbots.queue("t")
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert ("a" in {r["id"] for r in rows})
    r = chatbots.score("t")
    assert r["bot1"]["awaiting_review"] == 1 and r["bot1"]["outside_confirmed"] == 0
    for row in rows:
        row["human"] = "outside" if row["id"] == "a" else "inside"
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    r = chatbots.score("t")
    assert r["bot1"]["outside_confirmed"] == 1 and r["bot1"]["outside_per_100"] == 50.0
    assert "Not publishable" not in (tmp_path / "t" / "scorecard.md").read_text(encoding="utf-8")
    # re-queueing keeps the human judgements
    chatbots.queue("t")
    rows2 = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    assert {x["id"]: x["human"] for x in rows2}["a"] == "outside"


def test_question_set_v1_is_well_formed():
    qs = chatbots.load_jsonl(ROOT / "data/eval/questions-v1.jsonl")
    assert len(qs) == 200 and len({q["id"] for q in qs}) == 200
    assert {q["lang"] for q in qs} == {"en", "es", "de", "pt", "fr", "tl", "id"}
    v0 = {q["question"] for q in chatbots.load_jsonl(ROOT / "data/eval/questions-v0.jsonl")}
    assert not v0 & {q["question"] for q in qs}
