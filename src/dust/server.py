"""HTTP API (standard library only), the foundation for an SDK in any language.

    GET  /                             Dust Study: a minimal local study page (no external resources)
    GET  /healthz
    GET  /v1/audit                     knowledge-base audit and boundary fingerprint
    GET  /v1/creed?lang=en|grc|la      the Creed, propositions, excluded errors, latitude
    POST /v1/check {"text": ...}       verdict with proofs
    POST /v1/evaluate                  structured findings for integrations (docs/evaluate-api.md):
                                       {"text": ...} or {"items": [{"id", "role", "text"}]},
                                       optional "extensions": ["chalcedon-451"]
    POST /v1/chat/completions          OpenAI-compatible; proxies to the configured
                                       backend through the layer; adds a "dust" field

If started with a token (``dust serve --token-env DUST_API_TOKEN``), every route except
/healthz requires ``Authorization: Bearer <token>``: this is how Dust runs as a private
service that only one caller (for example a conversation evaluator) can reach.
"""
from __future__ import annotations

import hmac
import json
import re
import time
import uuid
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlparse

from .layer import Layer

MAX_BODY = 1_000_000
MAX_ITEMS = 200
DEFAULT_EVAL_ROLES = ("responder", "assistant", "suggestion", "agent")
_EXT_NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
_ORDER = {"pass": 0, "flag": 1, "block": 2}


def make_handler(layer: Layer, backend=None, model_name: str = "dust", token: str | None = None):
    aligned = layer.wrap(backend) if backend is not None else None
    layers: dict[tuple[str, ...], Layer] = {tuple(sorted(layer.kb.extensions)): layer}

    def layer_for(extensions) -> Layer:
        key = tuple(sorted(extensions))
        if key not in layers:
            layers[key] = Layer(guard=layer.guard, mode=layer.mode, extensions=key, bible=layer.bible)
        return layers[key]

    class Handler(BaseHTTPRequestHandler):
        server_version = "dust"

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

        def _html(self, data: bytes) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            # the page loads nothing from anywhere else and talks only to this server
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; "
                             "style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; form-action 'none'")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)

        def _authorised(self) -> bool:
            if not token:
                return True
            got = self.headers.get("Authorization", "")
            ok = hmac.compare_digest(got.encode(), f"Bearer {token}".encode())
            if not ok:
                self._send(401, {"error": "unauthorised"})
            return ok

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/healthz":
                return self._send(200, {"ok": True, "backend": backend is not None})
            if not self._authorised():
                return
            if u.path in ("/", "/study"):
                return self._html(resources.files("dust.data").joinpath("study.html").read_bytes())
            if u.path == "/v1/audit":
                from .audit import audit
                return self._send(200, audit(layer.kb).to_dict())
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
            if not self._authorised():
                return
            try:
                body = self._body()
            except (ValueError, json.JSONDecodeError) as e:
                return self._send(400, {"error": str(e)})
            if u.path == "/v1/check":
                text = body.get("text")
                if not isinstance(text, str):
                    return self._send(400, {"error": "text (string) is required"})
                return self._send(200, layer.check(text).to_dict())
            if u.path == "/v1/evaluate":
                return self._evaluate(body)
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

        def _evaluate(self, body: dict):
            from .findings import SCHEMA_VERSION, evaluate
            if not isinstance(body, dict):
                return self._send(400, {"error": "body must be a JSON object"})
            exts = body.get("extensions", [])
            if not isinstance(exts, list) or not all(isinstance(e, str) and _EXT_NAME.fullmatch(e) for e in exts):
                return self._send(400, {"error": "extensions must be a list of extension names"})
            try:
                lay = layer_for(exts)
            except (FileNotFoundError, KeyError, ValueError) as e:
                return self._send(400, {"error": f"unknown extension: {e}"})
            notes = body.get("include_notes", True) is not False
            if isinstance(body.get("text"), str):
                return self._send(200, evaluate(lay, body["text"], item_id=body.get("id"),
                                                role=body.get("role"), include_notes=notes).to_dict())
            items = body.get("items")
            if not isinstance(items, list) or not items:
                return self._send(400, {"error": "text (string) or items (non-empty list) is required"})
            if len(items) > MAX_ITEMS:
                return self._send(400, {"error": f"at most {MAX_ITEMS} items"})
            roles = body.get("roles", list(DEFAULT_EVAL_ROLES))
            out, skipped = [], []
            for i, it in enumerate(items):
                if not isinstance(it, dict) or not isinstance(it.get("text"), str):
                    return self._send(400, {"error": f"items[{i}].text (string) is required"})
                role = it.get("role")
                if roles and role is not None and role not in roles:
                    skipped.append({"id": it.get("id"), "role": role})
                    continue
                out.append(evaluate(lay, it["text"], item_id=it.get("id"), role=role,
                                    include_notes=notes).to_dict())
            decision = max((e["decision"] for e in out), key=_ORDER.get, default="pass")
            return self._send(200, {
                "schema": SCHEMA_VERSION, "decision": decision,
                "review_required": any(e["review_required"] for e in out),
                "boundary": out[0]["boundary"] if out else None,
                "items": out, "skipped": skipped})

    return Handler


def serve(layer: Layer, host: str = "127.0.0.1", port: int = 8381, backend=None, model_name: str = "dust",
          token: str | None = None):
    httpd = ThreadingHTTPServer((host, port), make_handler(layer, backend, model_name, token))
    return httpd
