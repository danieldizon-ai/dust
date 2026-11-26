import json
import threading
import urllib.error
import urllib.request

import pytest

from dust import Layer
from dust.findings import SCHEMA_VERSION, evaluate
from dust.server import serve

TOKEN = "t" * 32


@pytest.fixture(scope="module")
def layer():
    return Layer()


def test_contradiction_has_rule_evidence_and_review(layer):
    e = evaluate(layer, "Jesus is the archangel Michael.").to_dict()
    assert e["schema"] == SCHEMA_VERSION and e["decision"] == "block" and e["review_required"]
    f = e["findings"][0]
    assert f["rule_id"] == "P05" and f["kind"] == "doctrinal_contradiction" and f["method"] == "symbolic"
    assert f["evidence"]["sentence"] == "Jesus is the archangel Michael."
    assert any("R01" in step for step in f["evidence"]["proof"])
    assert f["excluded_errors"][0]["name"] == "Arianism"
    assert len(e["boundary"]["fingerprint"]) == 64


def test_denominational_difference_is_a_note_not_a_finding(layer):
    e = evaluate(layer, "We baptise infants, because the promise is for you and your children.").to_dict()
    assert e["decision"] == "pass" and e["findings"] == []
    assert [n["rule_id"] for n in e["notes"]] == ["L03"]


def test_latitude_overclaim_is_flagged(layer):
    e = evaluate(layer, "The Nicene Creed requires infant baptism.").to_dict()
    assert e["decision"] == "flag"
    assert e["findings"][0]["kind"] == "latitude_overclaim" and e["findings"][0]["rule_id"] == "L03"
    assert all(n["rule_id"] != "L03" for n in e["notes"])


def test_invalid_scripture_reference(layer):
    e = evaluate(layer, "As Jesus said in John 22:1, rejoice.").to_dict()
    f = [f for f in e["findings"] if f["kind"] == "scripture_reference"]
    assert f and f[0]["rule_id"] == "REF" and f[0]["review"]["required"]


def test_describing_is_not_asserting(layer):
    e = evaluate(layer, "Arius taught that the Son was created.").to_dict()
    assert e["decision"] == "pass"


@pytest.fixture(scope="module")
def private_server(layer):
    httpd = serve(layer, port=0, token=TOKEN)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _post(url, body, token=TOKEN):
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=h)
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_token_required(private_server):
    assert json.loads(urllib.request.urlopen(private_server + "/healthz").read())["ok"]
    for tok in (None, "wrong"):
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(private_server + "/v1/evaluate", {"text": "Christ is risen."}, token=tok)
        assert e.value.code == 401
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(private_server + "/v1/creed")
    assert e.value.code == 401


def test_evaluate_conversation_items(private_server):
    r = _post(private_server + "/v1/evaluate", {"items": [
        {"id": "m1", "role": "seeker", "text": "Is Jesus an angel?"},
        {"id": "m2", "role": "responder", "text": "No. The Son is true God from true God."},
        {"id": "m3", "role": "suggestion", "text": "The Holy Spirit is an impersonal force."},
    ]})
    assert r["decision"] == "block" and r["review_required"]
    assert [i["id"] for i in r["items"]] == ["m2", "m3"]
    assert r["skipped"] == [{"id": "m1", "role": "seeker"}]
    assert r["items"][0]["decision"] == "pass"
    assert r["items"][1]["findings"][0]["rule_id"] == "P17"


def test_evaluate_with_extension(private_server):
    r = _post(private_server + "/v1/evaluate", {"text": "Christ is risen.", "extensions": ["chalcedon-451"]})
    assert r["boundary"]["extensions"] == ["chalcedon-451"]
    base = _post(private_server + "/v1/evaluate", {"text": "Christ is risen."})
    assert base["boundary"]["fingerprint"] != r["boundary"]["fingerprint"]


@pytest.mark.parametrize("body", [{}, {"items": []}, {"items": [{"text": 3}]},
                                  {"text": "x", "extensions": ["../../etc"]}, {"text": "x", "extensions": ["nope"]}])
def test_evaluate_bad_requests(private_server, body):
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(private_server + "/v1/evaluate", body)
    assert e.value.code == 400
