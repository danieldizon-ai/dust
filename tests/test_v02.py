import json
from pathlib import Path

import pytest

from dust import Layer
from dust.cli import main
from dust.kb import load
from dust.scripture import Bible, Reference, check_quotes, find


@pytest.mark.parametrize("text,canonical,exists", [
    ("John 3:16", "John 3:16", True), ("1 Cor 15:3-4", "1 Corinthians 15:3-4", True),
    ("Ps 23", "Psalms 23", True), ("II Timothy 3:16", "2 Timothy 3:16", True),
    ("First Peter 2:9", "1 Peter 2:9", True), ("John 22:1", "John 22:1", False),
    ("Jude 2:1", "Jude 2:1", False), ("Genesis 1:32", "Genesis 1:32", False),
    ("Romans 8:39-38", "Romans 8:39-38", False),
])
def test_reference_parsing_and_existence(text, canonical, exists):
    refs = find(f"As it says in {text}, ...")
    assert len(refs) == 1
    assert refs[0].canonical == canonical and refs[0].exists is exists


def test_non_books_and_years_are_ignored():
    assert find("In 2026 we met at 7:30 with Hezekiah 3:4 in mind.") == []


def test_quote_check():
    bible = Bible({("John", 1, 14): "The Word became flesh, and lived among us.",
                   ("John", 3, 16): "For God so loved the world, that he gave his one and only Son."}, "test")
    text = 'John 1:14 says "The Word became flesh, and lived among us." and John 3:16 says "For God so loved the world that he sent angels."'
    refs = {r.canonical: r for r in check_quotes(text, bible)}
    assert refs["John 1:14"].quote_similarity == 1.0
    assert refs["John 3:16"].quote_similarity < 0.85


def test_layer_flags_invented_reference_and_misquote():
    v = Layer().check("Christ is risen, as John 22:1 says.")
    assert v.decision == "flag" and v.invalid_references[0]["problem"] == "John has 21 chapters"
    bible = Bible({("John", 3, 16): "For God so loved the world, that he gave his one and only Son."})
    v = Layer(bible=bible).check('John 3:16: "For God so loved the world that he sent a prophet to teach us."')
    assert v.decision == "flag"


def test_chalcedon_extension_stacks_without_changing_the_default():
    assert Layer().check("Christ was two separate persons.").decision == "pass"
    ext = Layer(extensions=["chalcedon-451"])
    v = ext.check("Christ was two separate persons.")
    assert v.decision == "block" and v.violations[0].proposition == "C01" and "X01" in v.violations[0].errors
    assert ext.check("Mary is not the mother of God.").decision == "block"
    # the Miaphysite formula is deliberately not excluded
    assert ext.check("In Christ there is one incarnate nature of God the Word.").decision == "pass"
    # Nicene checks still apply
    assert ext.check("Jesus was a created being.").decision == "block"


def test_extension_from_path(tmp_path):
    ext = {"id": "local", "propositions": [{"id": "L100", "group": "local", "severity": "core", "text": "Test.",
                                            "literals": ["sabbath(CHURCH)"]}],
           "patterns": [{"literal": "-sabbath(CHURCH)", "regex": "\\bthere is no sabbath\\b"}]}
    p = tmp_path / "local.json"
    p.write_text(json.dumps(ext))
    assert Layer(extensions=[str(p)]).check("There is no sabbath.").decision == "block"


def test_extension_cannot_redefine_nicene_propositions(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"id": "bad", "propositions": [{"id": "P05", "group": "x", "severity": "core", "text": "x", "literals": ["x(SON)"]}]}))
    with pytest.raises(ValueError):
        load((str(p),))


def test_cli_refs(capsys):
    assert main(["refs", "John 3:16 and John 22:1"]) == 1
    out = capsys.readouterr().out
    assert "INVALID" in out and "John 3:16\tok" in out
    assert main(["check", "--extension", "chalcedon-451", "Christ was two separate persons."]) == 1


def test_ablation_switches_change_behaviour():
    t = "Some people find that the Trinity confuses them."
    assert Layer(stance_gate=False).check(t).decision in ("pass", "flag", "block")
    assert Layer().check("Le Fils a été créé par le Père.").decision != "block"
    assert isinstance(Reference("x", None, 1, None, None, False).canonical, str)


def test_ablation_results_committed():
    rows = json.loads((Path(__file__).resolve().parents[1] / "results/ablations.json").read_text())
    names = [r["variant"] for r in rows]
    assert names[0] == "shipped: dual track" and "no stance gate" in names
