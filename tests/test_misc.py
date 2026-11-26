import json
import sys
from pathlib import Path

from dust.cli import main
from dust.kb import load
from dust.langid import detect
from dust.rag import rank

ROOT = Path(__file__).resolve().parents[1]


def test_rag_finds_the_right_articles():
    kb = load()
    assert "P17" in [p.id for p in rank(kb, "Is the Holy Spirit a force or a person?", 3)]
    assert "P13" in [p.id for p in rank(kb, "Did the tomb really end up empty on the third day?", 3)]
    assert "P05" in [p.id for p in rank(kb, "Was Jesus created like the angels?", 3)]


def test_langid():
    assert detect("Jesus is the Son of God.") == "en"
    assert detect("Jesús es el Hijo de Dios y no una criatura.") == "es"
    assert detect("Yesus adalah Anak Allah dan bukan ciptaan.") == "id"


def test_cli_exit_codes(capsys):
    assert main(["check", "Christ is risen."]) == 0
    assert main(["check", "Jesus was a created being."]) == 1
    assert main(["creed", "--lang", "la"]) == 0
    assert "Filioque" in capsys.readouterr().out


def test_training_generator_is_deterministic():
    sys.path.insert(0, str(ROOT / "training"))
    import generate
    assert generate.build() == generate.build()
    on_disk = [json.loads(line) for line in (ROOT / "data" / "train.jsonl").read_text(encoding="utf-8").splitlines()]
    assert on_disk == generate.build()


def test_eval_set_is_well_formed():
    rows = [json.loads(line) for line in (ROOT / "data" / "eval" / "nicene-eval-v0.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 307
    assert {r["label"] for r in rows} == {"contradicts", "consistent", "neutral"}
    assert len({r["id"] for r in rows}) == len(rows)
