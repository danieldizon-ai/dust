import json
import threading
import urllib.request

import pytest

from dust import Layer
from dust.backends import Scripted
from dust.server import serve


@pytest.fixture()
def server():
    httpd = serve(Layer(), port=0, backend=Scripted(["Christ is risen."]))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def test_health_and_creed(server):
    assert json.loads(urllib.request.urlopen(server + "/healthz").read())["ok"]
    c = json.loads(urllib.request.urlopen(server + "/v1/creed?lang=grc").read())
    assert len(c["propositions"]) == 24 and "Πιστεύομεν" in c["text"]


def test_check(server):
    v = _post(server + "/v1/check", {"text": "The Holy Spirit is an impersonal force."})
    assert v["decision"] == "block" and v["violations"][0]["proposition"] == "P17"


def test_chat_completions(server):
    r = _post(server + "/v1/chat/completions", {"model": "x", "messages": [{"role": "user", "content": "Did he rise?"}]})
    assert r["choices"][0]["message"]["content"] == "Christ is risen."
    assert r["dust"]["decision"] == "pass"


def test_bad_request(server):
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(server + "/v1/check", {"nope": 1})
    assert e.value.code == 400


def test_chat_behaviour_field(server):
    r = _post(server + "/v1/chat/completions", {"model": "x", "dust": {"behaviour": "annotate"},
                                                "messages": [{"role": "user", "content": "Did he rise?"}]})
    assert r["dust"]["behaviour"] == "annotate" and r["dust"]["decision"] == "pass"
    with pytest.raises(urllib.error.HTTPError) as e:
        _post(server + "/v1/chat/completions", {"model": "x", "dust": {"behaviour": "silent"},
                                               "messages": [{"role": "user", "content": "?"}]})
    assert e.value.code == 400
