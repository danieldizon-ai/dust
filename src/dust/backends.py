"""Model backends. Dust is model-agnostic: anything that turns messages into text.

* OpenAICompatible: llama.cpp server, Ollama (/v1), LM Studio, vLLM, Jan, or a hosted
  provider the user chooses. Uses only the standard library.
* Scripted: deterministic replies for tests and demos.
"""
from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Iterable


class OpenAICompatible:
    def __init__(self, base_url: str, model: str, api_key: str | None = None, timeout: float = 120.0,
                 temperature: float = 0.2, max_tokens: int = 700):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("DUST_API_KEY")
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

    def generate(self, messages: list[dict], **kw) -> str:
        body = json.dumps({"model": self.model, "messages": messages,
                           "temperature": kw.get("temperature", self.temperature),
                           "max_tokens": kw.get("max_tokens", self.max_tokens)}).encode()
        req = urllib.request.Request(self.base_url + "/chat/completions", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]


class Scripted:
    """Returns the given replies in order (cycling on the last one)."""

    def __init__(self, replies: Iterable[str]):
        self.replies = list(replies)
        self.calls: list[list[dict]] = []

    def generate(self, messages: list[dict], **kw) -> str:
        self.calls.append(messages)
        i = min(len(self.calls) - 1, len(self.replies) - 1)
        return self.replies[i]
