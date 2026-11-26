import pytest

from dust.symbolic import analyse, normalise, stance

BLOCK = [
    ("Jesus was a created being.", "P05", "E01"),
    ("There was a time when the Son was not.", "P04", "E01"),
    ("Jesus is the archangel Michael.", "P05", "E01"),
    ("Jesus was just a man.", "P06", "E05"),
    ("Jesus was a great moral teacher but not God.", "P06", "E05"),
    ("Jesus is a god, but not God Almighty.", "P07", "E02"),
    ("The Father, Son and Holy Spirit are just three modes of one person.", "P03", "E03"),
    ("Jesus became divine at his baptism.", "P04", "E04"),
    ("The Holy Spirit is an impersonal force.", "P17", "E06"),
    ("Jesus only seemed to be human.", "P11", "E07"),
    ("Jesus did not really die on the cross.", "P12", "E07"),
    ("The resurrection is just a metaphor.", "P13", "E13"),
    ("Jesus was crucified. He did not rise from the dead.", "P13", "E13"),
    ("Joseph was the biological father of Jesus.", "P10", "E12"),
    ("There are three gods.", "P01", "E10"),
    ("The material world was created by an evil god.", "P02", "E09"),
    ("His kingdom will come to an end.", "P16", "E11"),
    ("There is no resurrection of the dead.", "P23", "E15"),
    ("I deny that Jesus is God.", "P06", "E05"),
]

PASS = [
    "Jesus is not a creature but the eternal Son of God.",
    "Jesus was not just a man; he is fully God.",
    "It is false that Jesus was created.",
    "Arius taught that the Son was created.",
    "Some groups claim that the Holy Spirit is an impersonal force.",
    "Is Jesus a created being?",
    "If the Son were a creature, he could not save us.",
    "The Spirit proceeds from the Father and the Son.",
    "The Spirit proceeds from the Father through the Son.",
    "The Word became flesh and dwelt among us.",
    "Jesus was made man.",
    "Infants should be baptised.",
    "Only believers should be baptised.",
    "The resurrection is not a metaphor.",
    "They are not three gods.",
    "There was never a moment when the Son did not exist.",
    "Jesus did not survive the cross; he died.",
    "He did not stay in the tomb but rose on the third day.",
]


@pytest.mark.parametrize("text,prop,err", BLOCK)
def test_contradictions_are_found_with_the_right_article_and_error(text, prop, err):
    r = analyse(text)
    assert prop in {c.proposition for c in r.contradictions}, (text, r.claims)
    assert err in r.errors


@pytest.mark.parametrize("text", PASS)
def test_no_contradiction(text):
    r = analyse(text)
    assert not r.contradictions, (text, [(c.literal, c.stance) for c in r.claims])


def test_proof_chain_cites_rule_and_article():
    r = analyse("Jesus is an angel.")
    proofs = [step for c in r.contradictions for step in c.proof]
    assert any(step.startswith("R01") for step in proofs)
    assert any("contradicts P05" in step for step in proofs)


def test_entity_normalisation():
    assert normalise("The Holy Ghost and Jesus Christ") == ["SPIRIT and SON"]
    assert normalise("Father, Son and Spirit.")[0].startswith("FATHER, SON and SPIRIT")


@pytest.mark.parametrize("s,expected", [
    ("SON is GOD.", "assert"), ("arius taught that SON was created.", "reported"),
    ("is SON GOD?", "question"), ("if SON was created then", "hypothetical"),
    ("it is false that SON was created.", "reject"), ("i believe that SON is GOD.", "assert"),
])
def test_stance(s, expected):
    assert stance(s) == expected
