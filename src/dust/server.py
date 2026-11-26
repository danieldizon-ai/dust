"""HTTP API (standard library only), the foundation for an SDK in any language.

    GET  /healthz
    GET  /v1/creed?lang=en|grc|la      the Creed, propositions, excluded errors, latitude
    POST /v1/check {"text": ...}       verdict with proofs
    POST /v1/chat/completions          OpenAI-compatible; proxies to the configured
                                       backend through the layer; adds a "dust" field
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .layer import Layer

MAX_BODY = 1_000_000


def make_handler(layer: Layer, backend=None, model_name: str = "dust"):
    aligned = layer.wrap(backend) if backend is not None else None

    class Handler(BaseHTTPRequestHandler):
        server_version = "dust/0.1"

        def log_message(self, *a):  # quiet by default; no request logging = no content logging
            pass

        def _send(self, code: int, obj) -> None:
            data = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                raise ValueError("body too large")
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/healthz":
                return self._send(200, {"ok": True, "backend": backend is not None})
            if u.path == "/v1/creed":
                lang = parse_qs(u.query).get("lang", ["en"])[0]
                kb = layer.kb
                if lang not in kb.texts:
                    return self._send(400, {"error": f"lang must be one of {sorted(kb.texts)}"})
                return self._send(200, {
                    "title": kb.title, "version": kb.version, "attribution": kb.attribution,
                    "text": kb.texts[lang]["text"], "source": kb.texts[lang]["source"],
                    "propositions": [asdict(p) for p in kb.propositions],
                    "excluded_errors": [asdict(e) for e in kb.errors],
                    "latitude": kb.latitude})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            u = urlparse(self.path)
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, {"error": str(e)})
            if u.path == "/v1/check":
                text = body.get("text")
                if not isinstance(text, str):
                    return self._send(400, {"error": "text (string) is required"})
                return self._send(200, layer.check(text).to_dict())
            if u.path == "/v1/chat/completions":
                if aligned is None:
                    return self._send(503, {"error": "no backend configured; start with --backend URL --model NAME"})
                msgs = body.get("messages")
                if not isinstance(msgs, list):
                    return self._send(400, {"error": "messages (list) is required"})
                try:
                    r = aligned.chat(msgs)
                except Exception as e:  # backend failure
                    return self._send(502, {"error": f"backend error: {e}"})
                return self._send(200, {
                    "id": "chatcmpl-" + uuid.uuid4().hex[:12], "object": "chat.completion",
                    "created": int(time.time()), "model": model_name,
                    "choices": [{"index": 0, "finish_reason": "stop",
                                 "message": {"role": "assistant", "content": r.content}}],
                    "dust": {"decision": r.verdict.decision, "attempts": r.attempts, "repaired": r.repaired,
                             "refused": r.refused,
                             "violations": [asdict(v) for v in r.verdict.violations],
                             "flags": [asdict(v) for v in r.verdict.flags]}})
            self._send(404, {"error": "not found"})

    return Handler


def serve(layer: Layer, host: str = "127.0.0.1", port: int = 8381, backend=None, model_name: str = "dust"):
    httpd = ThreadingHTTPServer((host, port), make_handler(layer, backend, model_name))
    return httpd
