"""v0.3: input hardening, knowledge-base audit, metamorphic checks, study page."""
import dataclasses
import json
import threading
import urllib.request

import pytest

from dust import Layer
from dust.audit import audit, closure, fingerprint
from dust.cli import main
from dust.harden import sanitize, was_obfuscated
from dust.kb import Rule, load
from dust.server import serve

L = Layer()


# ---------------------------------------------------------------- hardening
@pytest.mark.parametrize("text", [
    "Jеsus was crеated.",                 # Cyrillic e
    "The S​on was cre​ated.",             # zero-width space
    "Jesus is an a-n-g-e-l.",                       # spaced letters
    "The Holy ⁠Spirit is an impersonal force.",
])
def test_obfuscated_claims_still_block(text):
    v = L.check(text)
    assert v.decision == "block" and v.obfuscated


def test_full_width_blocks():
    assert L.check("\uff2a\uff45\uff53\uff55\uff53 is an angel.").decision == "block"  # NFKC alone fixes it


def test_hardening_can_be_switched_off():
    assert Layer(sanitize=False).check("Jеsus was crеated.").decision == "pass"


def test_sanitize_leaves_greek_and_plain_text_alone():
    import unicodedata
    greek = unicodedata.normalize("NFKC", load().creed_text("grc"))
    assert sanitize(greek) == greek
    for t in ["U.S.A. and e.g. are fine.", "Christ is risen!", "Это русский текст."]:
        assert sanitize(t) == t and not was_obfuscated(t, sanitize(t))


# ---------------------------------------------------------------- metamorphic
CLAIMS = ["The Son was created.", "The Holy Spirit is an impersonal force.", "Jesus did not rise from the dead.",
          "Jesus is the archangel Michael.", "The Father, Son and Spirit are one person in three modes."]


@pytest.mark.parametrize("claim", CLAIMS)
def test_metamorphic_framing(claim):
    body = claim[0].lower() + claim[1:-1]
    assert L.check(claim).decision == "block"
    assert L.check(f"Arius taught that {body}.").decision != "block"            # reported
    assert L.check(f"Is it true that {body}?").decision != "block"              # question
    assert L.check(f"It is false that {body}.").decision != "block"            # rejected
    assert L.check(f"Honestly, between friends: {claim}").decision == "block"  # framing does not excuse


def test_report_frames_inner_rejection():
    assert L.check("Arius taught that it is wrong to say the Son is eternal.").decision != "block"


# ---------------------------------------------------------------- audit
def test_audit_passes_and_is_stable():
    r = audit()
    assert r.ok, r.problems
    assert r.fingerprint == fingerprint(load()) and len(r.fingerprint) == 64
    assert audit(load(("chalcedon-451",))).fingerprint != r.fingerprint
    assert r.stats["bad_references"] == 0


def test_audit_detects_an_inconsistent_rule():
    kb = load()
    bad = dataclasses.replace(kb, rules=kb.rules + [Rule("RX", "one_god(GOD)", ("created(SON)",), "test")],
                              axioms={})
    rep = audit(bad)
    assert not rep.ok and any("inconsistent" in p for p in rep.problems)
    assert rep.fingerprint != fingerprint(kb)


def test_closure_follows_rules():
    assert "created(SON)" in closure({"angel(SON)"}, load())


def test_cli_audit(capsys):
    assert main(["audit"]) == 0
    assert "fingerprint" in capsys.readouterr().out


# ---------------------------------------------------------------- server
@pytest.fixture()
def server():
    httpd = serve(Layer(), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def test_study_page_and_audit_endpoint(server):
    with urllib.request.urlopen(server + "/") as r:
        html = r.read().decode()
        assert "Dust Study" in html and "connect-src 'self'" in r.headers["Content-Security-Policy"]
        assert "http://" not in html.split("<script>")[0] and "https://" not in html
    a = json.loads(urllib.request.urlopen(server + "/v1/audit").read())
    assert a["ok"] and len(a["fingerprint"]) == 64


def test_cli_modelfile(capsys):
    assert main(["modelfile", "--base", "qwen2.5:1.5b-instruct"]) == 0
    out = capsys.readouterr().out
    assert "FROM qwen2.5:1.5b-instruct" in out and 'SYSTEM """' in out and "begotten" in out.lower()


# ---------------------------------------------------------------- lessons from the first end-to-end run
def test_creed_claims_about_latitude_are_flagged():
    v = L.check("The Nicene Creed affirms the baptism of infants as a sign of God's grace.")
    assert v.decision == "flag" and v.flags[0].source == "creed-claim" and v.flags[0].proposition == "L03"
    assert L.check("The Creed affirms one baptism for the forgiveness of sins.").decision == "pass"
    assert L.check("Infant baptism is not addressed directly in the Nicene Creed.").decision == "pass"


def test_trailing_aside_endorses_and_embedded_whether_does_not_assert():
    assert L.check("The Son is a creature, as the Arians believe.").decision == "block"
    assert L.check("The question of whether Jesus only seemed to be human is a matter of debate.").decision != "block"
    assert L.check("Christians believe that Jesus was created by God the Father.").decision == "block"


def test_creed_own_words_pass():
    assert L.check("Father, Son and Holy Spirit are truly distinct. They are not three names or modes "
                   "of a single person.").decision == "pass"


def test_refusal_needs_a_proof_and_reports_the_returned_text():
    from dust.backends import Scripted
    from dust.layer import Violation, Verdict
    # guard-only objection: at most one tentative rewrite, never a refusal; flagged if it persists
    class GuardSaysNo:
        meta = {}
        def scores(self, text):
            return {"contradicts": 0.99, "consistent": 0.005, "neutral": 0.005}
        def group(self, text):
            return "holy-spirit", 0.9
    lay = Layer(guard=GuardSaysNo())
    r = lay.wrap(Scripted(["The Spirit is with the church in every age."])).chat([{"role": "user", "content": "?"}])
    assert not r.refused and r.attempts == 2 and r.verdict.decision == "flag"
    # a guard-only objection that the rewrite satisfies: the rewrite is returned
    class GuardDislikesFirst(GuardSaysNo):
        def scores(self, text):
            bad = "una sola persona" in text
            return {"contradicts": 0.99 if bad else 0.01, "consistent": 0.5, "neutral": 0.49}
    lay = Layer(guard=GuardDislikesFirst())
    r = lay.wrap(Scripted(["La Trinidad es una sola persona divina.", "La Trinidad es un solo Dios en tres personas."])
                 ).chat([{"role": "user", "content": "?"}])
    assert r.repaired and not r.refused and r.content.endswith("tres personas.")
    # symbolic proof on every draft: refuse, and the reported verdict is for the fallback text
    r = L.wrap(Scripted(["Jesus was created."] * 3)).chat([{"role": "user", "content": "?"}])
    assert r.refused and r.verdict.decision != "block" and len(r.draft_verdicts) == 3
    assert all(v.decision == "block" for v in r.draft_verdicts)


# ---- run 2 findings (real-model transcripts, qwen2.5 3B)

def test_qualified_negation_is_not_a_denial():
    lay = Layer(mode="symbolic")
    s = "The Holy Spirit is not a person in the same way that the Father and Son are, but He is a person."
    assert lay.check(s).decision == "pass"
    assert lay.check("The Holy Spirit is not a person.").decision == "block"
    assert lay.check("The Holy Spirit is not a person, in the same way a force is not.").decision == "block"


def test_the_concept_of_is_reported():
    s = "However, the concept of Jesus being created by God is not a widely accepted view within Christian theology."
    assert Layer(mode="symbolic").check(s).decision == "pass"


def test_creed_silence_on_a_core_point_asks_for_a_repair():
    lay = Layer(mode="symbolic")
    for s in ["The Creed does not make any claims about Jesus being an archangel or any other angelic being.",
              "The Nicene Creed does not directly address whether Jesus was created by God."]:
        v = lay.check(s)
        assert v.decision == "block" and all(x.source == "creed-silence" for x in v.violations), s
    for s in ["The Creed says nothing about evolution.", "The Nicene Creed does not address infant baptism.",
              "The Creed does not address whether Mary was assumed into heaven."]:
        assert lay.check(s).decision == "pass", s


def test_assistant_agnostic_on_core_point_is_repaired():
    # run 3, qwen2.5 3B, q01
    lay = Layer(mode="symbolic")
    s = "Within the boundaries of the Nicene Creed, Dust cannot affirm or deny whether Jesus was created by God."
    v = lay.check(s)
    assert v.decision == "block" and [x.source for x in v.violations] == ["creed-silence"]
    from dust.backends import Scripted
    r = lay.wrap(Scripted([s, "No. The Creed confesses the Son as begotten, not made."])).chat([{"role": "user", "content": "?"}])
    assert r.repaired and not r.refused


def test_run3_false_positives():
    # qwen2.5 3B, run 3: q18, q13, q15 drafts
    lay = Layer(mode="symbolic")
    for s in ["Generally, these traditions do not consider Jesus to be an archangel.",
              "I'm sorry, but I can't engage in an argument that suggests Jesus was only a prophet.",
              "This is a core belief, and any assertion that the Son is a creature would be contrary to it."]:
        assert lay.check(s).decision == "pass", s
    for s in ["We consider Jesus to be an archangel.", "I don't think that Jesus is God."]:
        assert lay.check(s).decision == "block", s
