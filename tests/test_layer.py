from dust import Layer
from dust.backends import Scripted


def test_dual_blocks_with_symbolic_proof():
    v = Layer().check("Jesus was a created being.")
    assert v.decision == "block"
    assert v.violations[0].source == "symbolic" and v.violations[0].proof


def test_neural_catches_paraphrase_the_parser_misses():
    v = Layer().check("The Son is only a symbol of goodness and never truly God in any real sense.")
    assert v.decision == "block"
    assert any(x.source == "neural" for x in v.violations)


def test_reported_speech_is_not_blocked():
    assert Layer().check("Arius taught that there was a time when the Son was not.").decision == "pass"


def test_latitude_passes():
    layer = Layer()
    for t in ["Infants should be baptised.", "The Spirit proceeds from the Father and the Son.",
              "Purgatory exists.", "There is no purgatory."]:
        assert layer.check(t).decision == "pass", t


def test_unvalidated_language_can_only_flag():
    v = Layer().check("Le Fils a été créé par le Père et n'est pas Dieu.")
    assert v.decision in ("pass", "flag")


def test_translate_hook_pivots_to_english():
    v = Layer(translate=lambda s: "The Son was created by the Father.").check("Le Fils a été créé par le Père.")
    assert v.decision == "block"


def test_repair_loop():
    backend = Scripted(["Jesus was a created being.", "The Son is eternally begotten, not made."])
    r = Layer().wrap(backend).chat([{"role": "user", "content": "Was Jesus created?"}])
    assert r.repaired and not r.refused and r.attempts == 2
    assert "begotten" in r.content
    # the repair note cites the article that was violated
    assert "P05" in backend.calls[1][-1]["content"]


def test_fallback_when_model_keeps_contradicting():
    backend = Scripted(["Jesus was a created being."])
    r = Layer().wrap(backend, max_repairs=1).chat([{"role": "user", "content": "Was Jesus created?"}])
    assert r.refused and r.attempts == 2
    assert "John 1:3" in r.content


def test_system_prompt_is_grounded():
    p = Layer(mode="symbolic").system_prompt("Is the Holy Spirit a force?")
    assert "Nicene Creed" in p and "P17" in p and "2 Corinthians 3:17" in p
