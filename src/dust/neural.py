"""Neural track: a small hashed n-gram softmax classifier (the "guard").

It is a linear model, not a transformer: word 1-2 grams over the entity-normalised
text, plus character 3-5 grams over the raw text, hashed into 2**18 buckets, feeding
two softmax heads:

* verdict head: contradicts / consistent / neutral
* group head: which part of the Creed a contradiction concerns

Training is plain mini-batch Adam with L2, in numpy. Weights are stored int8 with one
scale per class (about 0.5 MB compressed), so the guard ships inside the package and
runs anywhere Python and numpy run, including a phone-class CPU. A fine-tuned
transformer guard is the obvious upgrade; see docs/methods.md for why this baseline
comes first and what it cannot do.
"""
from __future__ import annotations

import io
import json
import re
import zlib
from dataclasses import dataclass
from importlib import resources

import numpy as np

from .symbolic import normalise

N_FEATURES = 2 ** 18
LABELS = ["contradicts", "consistent", "neutral"]
_WORD = re.compile(r"[\w']+", re.UNICODE)


def _h(s: str) -> int:
    return zlib.crc32(s.encode("utf-8"))


def featurise(text: str, words: bool = True, chars: bool = True, entities: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """Return (indices, values) of the L2-normalised hashed feature vector.

    The flags exist for the ablation study (bench/ablations.py); the shipped guard uses
    all three."""
    feats: dict[int, float] = {}

    def add(key: str, w: float = 1.0) -> None:
        h = _h(key)
        idx = h % N_FEATURES
        sign = 1.0 if (h >> 31) & 1 == 0 else -1.0
        feats[idx] = feats.get(idx, 0.0) + sign * w

    if words:
        norm = " ".join(normalise(text)) if entities else text.lower()
        toks = _WORD.findall(norm)
        for i, w in enumerate(toks):
            add("w:" + w)
            if i + 1 < len(toks):
                add("b:" + w + " " + toks[i + 1])
            if i + 2 < len(toks):
                add("t:" + w + " " + toks[i + 1] + " " + toks[i + 2], 0.5)
    if chars:
        raw = " " + re.sub(r"\s+", " ", text.lower()) + " "
        for n in (3, 4, 5):
            for i in range(len(raw) - n + 1):
                add(f"c{n}:" + raw[i:i + n], 0.5)
    if not feats:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.float32)
    idx = np.fromiter(feats.keys(), dtype=np.int64)
    val = np.fromiter(feats.values(), dtype=np.float32)
    val /= np.linalg.norm(val) + 1e-9
    return idx, val


def _softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


@dataclass
class Guard:
    W: np.ndarray            # (N_FEATURES, n_labels) float32
    b: np.ndarray
    Wg: np.ndarray           # group head
    bg: np.ndarray
    groups: list[str]
    meta: dict

    def _feats(self, text: str):
        f = self.meta.get("feature_flags") or {}
        return featurise(text, **f)

    def scores(self, text: str) -> dict[str, float]:
        idx, val = self._feats(text)
        z = (self.W[idx] * val[:, None]).sum(axis=0) + self.b
        p = _softmax(z)
        return {lab: float(p[i]) for i, lab in enumerate(LABELS)}

    def group(self, text: str) -> tuple[str, float]:
        idx, val = self._feats(text)
        z = (self.Wg[idx] * val[:, None]).sum(axis=0) + self.bg
        p = _softmax(z)
        k = int(p.argmax())
        return self.groups[k], float(p[k])

    # ---------------------------------------------------------------- persistence
    def save(self, path) -> None:
        def q(w):
            scale = np.abs(w).max(axis=0) / 127.0 + 1e-12
            return np.round(w / scale).astype(np.int8), scale.astype(np.float32)
        Wq, Ws = q(self.W)
        Wgq, Wgs = q(self.Wg)
        np.savez_compressed(path, Wq=Wq, Ws=Ws, b=self.b, Wgq=Wgq, Wgs=Wgs, bg=self.bg,
                            meta=np.frombuffer(json.dumps({**self.meta, "groups": self.groups}).encode(), dtype=np.uint8))

    @classmethod
    def load_file(cls, fh) -> "Guard":
        z = np.load(fh)
        meta = json.loads(bytes(z["meta"]).decode())
        groups = meta.pop("groups")
        return cls(z["Wq"].astype(np.float32) * z["Ws"], z["b"], z["Wgq"].astype(np.float32) * z["Wgs"], z["bg"], groups, meta)

    @classmethod
    def load(cls) -> "Guard":
        data = resources.files("dust.data").joinpath("guard-v0.npz").read_bytes()
        return cls.load_file(io.BytesIO(data))


def _batches(n: int, size: int, rng: np.random.Generator):
    order = rng.permutation(n)
    for i in range(0, n, size):
        yield order[i:i + size]


def train_head(X: list[tuple[np.ndarray, np.ndarray]], y: np.ndarray, n_classes: int, *, epochs: int = 30,
               lr: float = 0.05, l2: float = 1e-5, seed: int = 0, class_weight: np.ndarray | None = None):
    """Sparse softmax regression with Adam. Returns (W, b)."""
    rng = np.random.default_rng(seed)
    W = np.zeros((N_FEATURES, n_classes), dtype=np.float32)
    b = np.zeros(n_classes, dtype=np.float32)
    mW = np.zeros_like(W); vW = np.zeros_like(W)
    mb = np.zeros_like(b); vb = np.zeros_like(b)
    b1, b2, eps, t = 0.9, 0.999, 1e-8, 0
    cw = class_weight if class_weight is not None else np.ones(n_classes, dtype=np.float32)
    for _ in range(epochs):
        for batch in _batches(len(X), 32, rng):
            t += 1
            rows = np.concatenate([np.full(len(X[i][0]), j) for j, i in enumerate(batch)])
            cols = np.concatenate([X[i][0] for i in batch])
            vals = np.concatenate([X[i][1] for i in batch]).astype(np.float32)
            Z = np.zeros((len(batch), n_classes), dtype=np.float32)
            np.add.at(Z, rows, W[cols] * vals[:, None])
            Z += b
            P = _softmax(Z)
            Y = np.zeros_like(P); Y[np.arange(len(batch)), y[batch]] = 1.0
            G = (P - Y) * cw[y[batch]][:, None] / len(batch)
            gW_rows = G[rows] * vals[:, None]
            uniq, inv = np.unique(cols, return_inverse=True)
            gW = np.zeros((len(uniq), n_classes), dtype=np.float32)
            np.add.at(gW, inv, gW_rows)
            gW += l2 * W[uniq]
            gb = G.sum(axis=0)
            # Adam (lazy, on touched rows only)
            mW[uniq] = b1 * mW[uniq] + (1 - b1) * gW
            vW[uniq] = b2 * vW[uniq] + (1 - b2) * gW ** 2
            W[uniq] -= lr * (mW[uniq] / (1 - b1 ** t)) / (np.sqrt(vW[uniq] / (1 - b2 ** t)) + eps)
            mb = b1 * mb + (1 - b1) * gb
            vb = b2 * vb + (1 - b2) * gb ** 2
            b -= lr * (mb / (1 - b1 ** t)) / (np.sqrt(vb / (1 - b2 ** t)) + eps)
    return W, b
