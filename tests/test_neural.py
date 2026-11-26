import io

import numpy as np

from dust.neural import LABELS, Guard, featurise, train_head


def test_guard_ships_and_scores():
    g = Guard.load()
    s = g.scores("Jesus was only a man.")
    assert set(s) == set(LABELS) and abs(sum(s.values()) - 1) < 1e-5
    assert s["contradicts"] > s["consistent"]
    assert g.meta["licence"] == "Apache-2.0"


def test_featurise_deterministic():
    a = featurise("Jesus is Lord")
    b = featurise("Jesus is Lord")
    assert np.array_equal(a[0], b[0]) and np.allclose(a[1], b[1])


def test_tiny_training_and_int8_roundtrip(tmp_path):
    texts = ["the son was created", "the son is eternal", "the son was made", "the son is begotten"] * 5
    y = np.array([0, 1, 0, 1] * 5)
    X = [featurise(t) for t in texts]
    W, b = train_head(X, y, 3, epochs=10, seed=0)
    g = Guard(W, b, W[:, :2].copy(), b[:2].copy(), ["a", "b"], {"name": "t"})
    path = tmp_path / "g.npz"
    g.save(path)
    g2 = Guard.load_file(io.BytesIO(path.read_bytes()))
    assert abs(g.scores("the son was created")["contradicts"] - g2.scores("the son was created")["contradicts"]) < 0.05
    assert g2.scores("the son was created")["contradicts"] > g2.scores("the son is eternal")["contradicts"]
