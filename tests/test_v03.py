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
