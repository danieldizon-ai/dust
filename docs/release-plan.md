# Catching up, fine-tuning and releasing the Dust model family

Dust does not train base models from scratch, and should not try. Pretraining a competitive
model costs millions of dollars and a team; open-weight makers already spend that and give
the results away. Dust's job is to **adopt** the best open models as they appear,
**measure** them against the boundary, **adapt** them where the measurement shows a gap,
and **release** the result as a family people can download. This page is the plan for
doing that, with realistic compute.

## Stages

| Stage | What happens | Output | Compute | Gate to the next stage |
|---|---|---|---|---|
| 0. Prompt layer | Wrap an open model with the constitution, Creed, retrieval, checker and repair loop | Works today with any OpenAI-compatible server; `dust modelfile` makes an Ollama model that carries the prompt | None | - |
| 1. Measure | Run `bench/e2e.py` on candidate bases per tier, raw versus wrapped; read transcripts | A scorecard per model and language | One laptop or desktop; hours | Scorecard published for at least 3 tiers |
| 2. Adapt | LoRA/QLoRA + DPO on reviewed preference pairs for the bases that need it | Adapters of tens of MB per tier | One 24 GB GPU for a 3-8B model, a few hours per run; or a managed service such as Thinking Machines' Tinker | Adapter beats prompt layer on e2e, without losing on general benchmarks or the maker's safety tests |
| 3. Distil | A large model behind the full Dust loop generates checked, reviewed answers; small models are tuned on them | Better small tiers, plus an open dataset | Inference on a 70B-class model for days (rented), then stage-2 training per tier | Small tier closes measurable gap to large on e2e |
| 4. Quantise | Merge adapters, quantise to 4-8 bit (GGUF for llama.cpp/Ollama; MLX for Apple) and re-run the benchmark at each bit width | Downloadable files per tier | CPU or one GPU; hours | Doctrinal score at 4-bit within an agreed margin of 16-bit |
| 5. Release | Publish weights with model cards, evaluation, licence notices and pinned base revision | `dust-pocket`, `dust-small`, `dust-base`, `dust-large` | - | Licence allows it; reviewers sign off |
| 6. Maintain | Re-run stage 1 on each notable new open release (monthly, as Always proposed); retrain adapters only when a new base wins | Updated scorecards | Hours per month | - |

## Catching up: why adopt, not build

Open models trail the frontier by months, not years, and distillation and quantisation
bring that capability down to laptops and phones ([open-models.md](open-models.md)). The
cheapest way for Dust to stay current is to keep its alignment *outside* the weights
wherever possible, so a new base can be swapped in the week it is released, and to keep
adapters small so retraining per base costs hours, not weeks. Thinking Machines Lab's
results on LoRA (that well-configured LoRA matches full fine-tuning in many post-training
settings) are the main reason to expect adapters to be enough.

## Naming and what a release contains

`dust-<tier>-<base>-v<version>`, for example `dust-small-qwen2.5-3b-v1`. Each release has:

* the merged weights in GGUF (and the adapter alone, for people who prefer to merge
  themselves), with SHA-256 hashes;
* a model card: base model and revision, licence and notices, training data (all of it
  public), the boundary fingerprint it was trained against, the e2e scorecard and the
  checker benchmark, known failure modes;
* an Ollama Modelfile, so `ollama create` works offline.

**The layer still runs on top of a released model.** Fine-tuning moves the defaults; the
checker and repair loop are still what make a block explainable.

## Where releases are published

Only in this repository's releases, or as Hugging Face drafts that Daniel uploads himself.
Bases must allow derivatives and redistribution without field-of-use restrictions
(Apache-2.0, MIT or equivalent); see the licence rule in [model-family.md](model-family.md).

## What would need more than this project has

* Preference data reviewed by people from several traditions (the main cost is people).
* A 70B-class teacher run for distillation: rented GPUs for some days.
* Multilingual review for each released language.
* Pretraining or continued pretraining on theological corpora: out of scope unless a
  partner with the compute wants to do it; the plan above does not depend on it.
