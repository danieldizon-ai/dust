# Dust

**A Nicene Creed (381) alignment layer for open language models.**

Dust is a personal research project led by Daniel Dizon and **incubated by Rejoice**, a
Christian technology company that invests in, operates and builds for the faith and
flourishing ecosystem. It builds on research by **Always Foundation** (see
[docs/lineage.md](docs/lineage.md)).

Every open model already ships aligned to its maker's specification. Dust adds one more
layer on top, and only one: the Niceno-Constantinopolitan Creed of AD 381, the oldest
confession shared by Catholic, Orthodox and Protestant Christians. It is infrastructure,
not an app: a Python package and an OpenAI-compatible HTTP API that any study tool, Bible
app or ministry product can put in front of any open model, on the user's own device.

> "Dust" because the layer is small enough to go anywhere, and because of Genesis 2:7.

## What it does

```
question ──► constitution + Creed + the relevant articles and verses ──► any open model
                                                                            │ draft
                ┌───────────────────────────────────────────────────────────┘
                ▼
        sentence by sentence:
        symbolic track: parse ► stance ► literals ► rules ► contradiction + proof
        neural track:   197 KB int8 guard, gated by the parser's stance
                │
     pass ◄─────┼─────► block ► repair note citing the article ► regenerate (x2) ► cited fallback
                ▼
              flag (outside validated languages, or low confidence)
```

* **The boundary, made checkable.** 24 propositions from the Creed with Greek anchors and
  Scripture, 16 excluded historic errors (Arianism, modalism, docetism ... each tied to the
  articles it contradicts), 11 latitude topics the Creed leaves open, 16 inference rules.
  [`src/dust/data/creed.json`](src/dust/data/creed.json)
* **Dual-track checking**: a transparent symbolic checker whose every block comes with a
  proof, plus a small neural guard for paraphrase.
* **Describing is not asserting.** "Arius taught that the Son was created" passes; "the Son
  was created" is blocked with a proof citing P05 (*begotten, not made*).
* **Fair beyond the Creed.** Infant and believer's baptism, the Filioque either way,
  justification, purgatory, the millennium: all pass.
* **Repair, not just refusal.** A blocked draft goes back to the model with the article it
  contradicted; only if it fails twice does Dust return a cited fallback.

```
$ dust check "Jesus is the archangel Michael."
BLOCK
  BLOCK P05 via symbolic (1.00): Jesus is the archangel Michael.
      claim: "SON is the archangel" => angel(SON)
      R01: angel(SON) -> created(SON) (An angel is a creature.)
      contradicts P05 (-created(SON)): The Son is begotten, not made: he is not a creature.
  BLOCK P04 via symbolic (1.00): ...   (R02: created -> not eternal)
  BLOCK P06 via symbolic (1.00): ...   (R02: created -> not true God)
```

## Results

Doctrinal-consistency benchmark: 307 hand-labelled items in 7 languages, including traps
(reported views, negation, latitude positions, analogies, multi-sentence answers). Held-out
test split, n=153; positive class = the text asserts something the Creed excludes.

| system | precision | recall | F1 | false-positive rate |
|---|---|---|---|---|
| keyword baseline | 0.545 | 0.203 | 0.296 | 0.106 |
| symbolic only | 0.963 | 0.441 | 0.605 | 0.011 |
| neural only | 0.733 | 0.559 | 0.635 | 0.128 |
| **Dust (dual track)** | **0.872** | **0.695** | **0.774** | **0.064** |

Checking costs a median 0.45 ms per sentence on a CPU. Read
[docs/evaluation.md](docs/evaluation.md) before quoting these: they measure the checker,
not a model (no base model could be run in the sandbox that built v0.1); one author wrote
both training and evaluation data; the first-run numbers (F1 0.807, false positives 12.8%)
are kept for comparison. Every error is listed in [results/benchmark.md](results/benchmark.md).
Paraphrase recall (0.64) and non-English coverage are the weak points.

## Quickstart

```bash
pip install git+https://github.com/DanielDizon-AI/dust
dust check "The Holy Spirit is an impersonal force."
dust creed --lang grc
dust prompt "Is the Holy Spirit a person?"     # grounded system prompt
```

```python
from dust import Layer
from dust.backends import OpenAICompatible

layer = Layer()
print(layer.check("The resurrection is just a metaphor.").decision)   # block

model = layer.wrap(OpenAICompatible("http://localhost:11434/v1", "qwen2.5:3b-instruct"))  # Ollama, llama.cpp, LM Studio, vLLM...
r = model.chat([{"role": "user", "content": "Was Jesus created?"}])
print(r.content, r.verdict.decision, r.attempts)
```

As an API (standard library only; binds to localhost, logs nothing):

```bash
dust serve --backend http://localhost:11434/v1 --model qwen2.5:3b-instruct
curl -s localhost:8381/v1/check -d '{"text":"Jesus was only a prophet."}'
curl -s localhost:8381/v1/chat/completions -d '{"messages":[{"role":"user","content":"Who is Jesus?"}]}'
```

`/v1/chat/completions` is OpenAI-compatible, so existing clients work unchanged; the
response carries an extra `dust` field with the decision, repairs and proofs.

## Documentation

| | |
|---|---|
| [docs/theology.md](docs/theology.md) | The boundary: what is inside and outside, why 381 (not smaller, not Chalcedon), the Filioque, what Dust does not decide, and why a minimum does not compromise the gospel |
| [docs/methods.md](docs/methods.md) | Prompts, retrieval, guard models, LoRA/DPO, constrained decoding and the neurosymbolic dual track, with trade-offs and where neurosymbolic stops being practical |
| [docs/evaluation.md](docs/evaluation.md) | Benchmark method, iteration history and limits |
| [docs/model-family.md](docs/model-family.md) | One layer across pocket to max tiers; candidate base models and licences |
| [docs/open-models.md](docs/open-models.md) | Open models catching up through distillation and quantisation |
| [docs/hardware.md](docs/hardware.md) | What runs where |
| [docs/privacy.md](docs/privacy.md) | On-device by default, Obsidian-style end-to-end encrypted sync, access in censored and adversarial environments |
| [docs/uses.md](docs/uses.md) | Scripture study, multilingual use, and what Dust is not for |
| [docs/lineage.md](docs/lineage.md) | Rejoice, Always Foundation and what Dust adds |

## Repository

```
src/dust/          the package: kb, symbolic, neural, layer, rag, backends, server, cli
src/dust/data/     creed.json, rules.json, constitution.md, scripture.json, guard-v0.npz
data/train.jsonl   synthetic training data (training/generate.py, seeded)
data/eval/         hand-labelled benchmark and end-to-end questions
bench/             run.py (checker benchmark), e2e.py (full loop against a real model)
training/          generate, train_guard, dpo_pairs, lora_dpo (recipe, not yet run)
results/           benchmark.md/json, first-run.md/json
```

Everything is reproducible on a laptop CPU in under a minute:

```bash
pip install -e '.[dev]'
pytest -q                                   # 73 tests
python training/generate.py && python training/train_guard.py
python bench/run.py --check                 # fails if any benchmark count changes
```

## Status and next steps

v0.1 is a research prototype. It has not been reviewed by theologians from several
traditions, no base model has been run through it, and no adapter has been trained. In
priority order:

1. Run `bench/e2e.py` on the family's base models and publish transcripts.
2. Theological review of `creed.json` by Catholic, Orthodox and Protestant readers, and an
   evaluation set written by people other than the author.
3. A small-LM semantic parser feeding the rule engine (the AlphaGeometry-style split) and a
   multilingual transformer guard.
4. LoRA/DPO adapters per tier where the end-to-end results show the need.

## Licence

Code and the guard weights: Apache-2.0 ([LICENSE](LICENSE)). Creed propositions and parts
of the documentation are adapted from Always Foundation under CC BY 4.0; Creed texts and
the World English Bible are public domain. See [NOTICE](NOTICE).
