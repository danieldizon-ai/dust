# Dust

**A Nicene Creed (381) alignment layer for open language models: free, open, private AI for the global Church.**

Dust is a personal research project led by Daniel Dizon and **incubated by Rejoice**, a
Christian technology company that invests in, operates and builds for the faith and
flourishing ecosystem. It builds on research by **Always Foundation** (see
[docs/lineage.md](docs/lineage.md)).

Every open model already ships aligned to its maker's specification. Dust adds one more
layer on top, and only one: the Niceno-Constantinopolitan Creed of AD 381, the oldest
confession shared by Catholic, Orthodox and Protestant Christians. It is infrastructure,
not an app: a Python package and an OpenAI-compatible HTTP API that any study tool, Bible
app or ministry product can put in front of any open model, on the user's own device.

Use it two ways: as **infrastructure** (put it in front of any open model in your app) or
directly, as **Dust Study**, a minimal local study page that `dust serve` opens in your
browser. Churches and denominations can stack their own confession on top as a profile, or
fork it; the boundary fingerprint shows which boundary a deployment enforces. Why this
matters, and what it costs: [docs/mission.md](docs/mission.md), [docs/economics.md](docs/economics.md).

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
* **Scripture is checked, not trusted.** Invented references ("John 22:1") are flagged; with a
  Bible text loaded, misquotations are too.
* **A stack, not a ceiling.** A church can add its own confession as an extension file on top
  of the Creed without changing the default; Ephesus and Chalcedon ship as the worked example.
* **Hardened.** Look-alike letters, invisible characters and spaced-out words are undone
  before checking (all 78 base contradictions still blocked; up to 100% evaded without it),
  and `dust audit` proves the encoded boundary is consistent and fingerprints it.
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
| neural only | 0.806 | 0.424 | 0.556 | 0.064 |
| **Dust (dual track)** | **0.925** | **0.627** | **0.747** | **0.032** |

Checking costs a median 0.48 ms per sentence on a CPU. Read
[docs/evaluation.md](docs/evaluation.md) before quoting these: one author wrote both
training and evaluation data, and earlier iterations (first run F1 0.807 with 12.8% false
positives; v0.2 F1 0.774 with 6.4%) are kept for comparison. Every error is listed in
[results/benchmark.md](results/benchmark.md). Paraphrase recall (0.52) and non-English
coverage are the weak points.

**On real models.** The full loop has been run three times on qwen2.5 1.5B and 3B on an
ordinary desktop (4 GB GPU, 8 GB RAM), with every answer read by hand. Across the three runs
the raw models stated something the Creed excludes in 25 of 150 answers; through Dust, 6, all
in German or Spanish, where the rules cannot read. The first run refused 12 answers, mostly
good ones; after requiring a proof before any refusal, runs 2 and 3 refused 2 and 3, and just
one of run 3's refusals turned away a good answer. Small sample, one reader, and the fixes were
tuned on the same 25 questions: [run 1](results/e2e/run1-review.md),
[run 2](results/e2e/run2-review.md), [run 3](results/e2e/run3-review.md).

The ablation study ([results/ablations.md](results/ablations.md)) shows what matters: removing
the stance gate (which separates *saying* a heresy from *describing* one) more than doubles
false positives; removing the 16 inference rules cuts recall from 0.61 to 0.41.

## Quickstart

```bash
pip install git+https://github.com/DanielDizon-AI/dust
dust check "The Holy Spirit is an impersonal force."
dust creed --lang grc
dust prompt "Is the Holy Spirit a person?"     # grounded system prompt
dust refs "See John 3:16 and John 22:1"         # which references exist
dust check --extension chalcedon-451 "Christ was two persons."
dust audit                                      # consistency, coverage, boundary fingerprint
dust modelfile --base qwen2.5:3b-instruct > Modelfile   # prompt layer as an Ollama model
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

Open `http://127.0.0.1:8381` for Dust Study. `GET /v1/audit` returns the boundary
fingerprint. `/v1/chat/completions` is OpenAI-compatible, so existing clients work unchanged; the
response carries an extra `dust` field with the decision, repairs and proofs.

## Documentation

| | |
|---|---|
| [docs/findings.md](docs/findings.md) | **Start here.** What we built, what the numbers show, what we learned, where it falls short, conclusion |
| [docs/roadmap.md](docs/roadmap.md) | Next steps for whoever takes it forward, with acceptance criteria |
| [docs/mission.md](docs/mission.md) | Free, open, private AI for the global Church; one boundary, many profiles; infrastructure and a direct app |
| [docs/economics.md](docs/economics.md) | Cost per user hosted versus on-device, and why free, open, private and sovereign matter |
| [docs/release-plan.md](docs/release-plan.md) | Catching up with open models: measure, adapt, distil, quantise, release the family |
| [docs/hardening.md](docs/hardening.md) | Hardening the encoding, the checker and the governance of the boundary |
| [docs/prior-work.md](docs/prior-work.md) | Credit: Always Foundation, Magisterium AI, church statements on AI, open data and open models |
| [docs/theology.md](docs/theology.md) | The boundary: what is inside and outside, why 381 (not smaller, not Chalcedon), the Filioque, what Dust does not decide, and why a minimum does not compromise the gospel |
| [docs/methods.md](docs/methods.md) | Prompts, retrieval, guard models, LoRA/DPO, constrained decoding and the neurosymbolic dual track, with trade-offs and where neurosymbolic stops being practical |
| [docs/evaluation.md](docs/evaluation.md) | Benchmark method, iteration history and limits |
| [results/ablations.md](results/ablations.md) | 16 variants: which parts of the system matter |
| [results/hardening.md](results/hardening.md) | Evasion and framing robustness |
| [docs/extensions.md](docs/extensions.md) | Stacking a church's confession on top of the Creed |
| [docs/model-family.md](docs/model-family.md) | One layer across pocket to max tiers; candidate base models and licences |
| [docs/open-models.md](docs/open-models.md) | Open models catching up through distillation and quantisation |
| [docs/hardware.md](docs/hardware.md) | What runs where |
| [docs/privacy.md](docs/privacy.md) | On-device by default, Obsidian-style end-to-end encrypted sync, access in censored and adversarial environments |
| [docs/uses.md](docs/uses.md) | Scripture study, multilingual use, and what Dust is not for |
| [docs/lineage.md](docs/lineage.md) | Rejoice, Always Foundation and what Dust adds |

## Repository

```
src/dust/          the package: kb, symbolic, neural, layer, harden, audit, scripture, rag, langid, backends, server, cli
src/dust/data/     creed.json, rules.json, constitution.md, scripture.json, versification.json,
                   guard-v0.npz, study.html, extensions/chalcedon-451.json
data/train.jsonl   synthetic training data (training/generate.py, seeded)
data/eval/         hand-labelled benchmark and end-to-end questions
bench/             run.py (checker benchmark), ablations.py, hardening.py, e2e.py (full loop against a real model)
training/          generate, train_guard, dpo_pairs, lora_dpo (recipe, not yet run)
results/           benchmark, first-run, ablation and hardening results
```

Everything is reproducible on a laptop CPU in under a minute:

```bash
pip install -e '.[dev]'
pytest -q                                   # 114 tests
python training/generate.py && python training/train_guard.py
python bench/run.py --check                 # fails if any benchmark count changes
python bench/ablations.py                   # retrains 5 guard variants, ~1 minute
python bench/hardening.py --check           # evasion and framing robustness
dust audit                                  # the boundary is consistent and unchanged
```

## Status and next steps

v0.3 is a research prototype. It has not been reviewed by theologians from several
traditions, it has been run end to end on only two small models, and no adapter has been
trained. The
full plan, with acceptance criteria, is in [docs/roadmap.md](docs/roadmap.md). In short:

1. Run `bench/e2e.py` on more and larger base models with a new, unseen question set (about 200, all seven languages), and publish transcripts.
2. Theological review of `creed.json` by Catholic, Orthodox and Protestant readers, and an
   evaluation set written by people other than the author.
3. A small-LM semantic parser feeding the rule engine (the AlphaGeometry-style split), a
   multilingual transformer guard, and validated multilingual checking.
4. LoRA/DPO adapters per tier where the end-to-end results show the need, then distil,
   quantise and release the family ([docs/release-plan.md](docs/release-plan.md)).

## Licence

Code and the guard weights: Apache-2.0 ([LICENSE](LICENSE)). Creed propositions and parts
of the documentation are adapted from Always Foundation under CC BY 4.0; Creed texts and
the World English Bible are public domain. See [NOTICE](NOTICE).
