from dust.kb import load, negate


def test_counts_and_ids():
    kb = load()
    assert len(kb.propositions) == 24
    assert len(kb.errors) == 16
    assert len(kb.latitude) == 11
    assert len({p.id for p in kb.propositions}) == 24


def test_every_error_points_at_real_propositions():
    kb = load()
    ids = {p.id for p in kb.propositions}
    for e in kb.errors:
        assert e.contradicts and set(e.contradicts) <= ids, e.id


def test_every_error_has_a_signature_that_contradicts_an_axiom_after_rules():
    from dust.symbolic import Claim, infer
    kb = load()
    for eid, sig in kb.error_signatures.items():
        hits = []
        for lit in sig:
            res = infer([Claim(lit, 0, "assert", lit)], kb)
            hits += [c.proposition for c in res.contradictions]
        assert set(hits) & set(kb.error(eid).contradicts), eid


def test_scripture_present_for_every_reference():
    kb = load()
    for p in kb.propositions:
        for ref, text in kb.verses(p.id):
            assert text.strip(), ref


def test_texts_and_filioque():
    kb = load()
    assert "proceeds from the Father;" in kb.creed_text("en")
    assert "and the Son" not in kb.creed_text("en").split("proceeds from the Father")[1][:20]
    assert "Filioque" in kb.creed_text("la")
    assert "ὁμοούσιον" in kb.creed_text("grc")


def test_negate():
    assert negate("a(X)") == "-a(X)" and negate("-a(X)") == "a(X)"


def test_attribution_to_always_foundation():
    assert "Always Foundation" in load().attribution
