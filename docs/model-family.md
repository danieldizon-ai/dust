# The Dust family: one layer, many model sizes

Mistral's early releases showed a pattern worth copying: a family of open models from
small to large, sharing one design, so a developer picks the size that fits the device
and moves up or down without relearning anything. Dust applies that idea to alignment.
**The layer is the constant; the base model is the variable.** Every tier gets the same
Creed, constitution, retrieval, checker and repair loop, and later the same adapter
recipe, so behaviour can be compared tier against tier on the same benchmark.

Dust does not train base models. It selects open-weight models by licence and evaluation
and wraps them.

## Tiers

| Tier | Target hardware | Base model size (4-bit) | Typical use |
|---|---|---|---|
| `dust-pocket` | Phones, browser (WebGPU/WASM), Raspberry Pi 5 | 1-2B (~0.7-1.5 GB) | Offline Scripture lookup and short explanations; checker does most of the work |
| `dust-small` | Laptops with 8 GB memory | 3-4B (~2-3 GB) | Personal study tool |
| `dust-base` | 16 GB laptops, Apple silicon | 8-12B (~5-8 GB) | Default for serious study and teaching preparation |
| `dust-large` | Workstations, 24-48 GB GPUs or 64 GB Macs | 24-32B (~15-20 GB) | Seminaries, translation teams, church servers |
| `dust-max` | Multi-GPU servers | 70B+ or mixture-of-experts | Research, generating and reviewing training data |

The guard and symbolic checker are identical in every tier and need about 200 KB and a
millisecond of CPU per sentence, so even the pocket tier gets the full checker.

## Candidate base models

Always Foundation's monthly-reviewed recommendation set (`ai/models/recommended.json`,
reviewed 24 November 2026) lists Apache-2.0 models for three of these tiers: Gemma 4 E2B
(small), Gemma 4 E4B or Qwen3.5 4B (standard) and Gemma 4 12B quantisation-aware (large),
with Qwen3 Embedding 0.6B for retrieval. Dust adopts that set as its starting point.
These names come from Always's review; the sandbox that built Dust v0.1 could not reach
Hugging Face, so they were not re-verified here. Re-check model cards before use.

Always's RFC 0007 also names Inkling 2 Mini from Thinking Machines Lab as an Apache-2.0
open-weight model of about 20 GB. Dust treats every such model the same way: a
candidate, not a dependency, adopted only after it is run through the benchmark.

Other long-standing open families to consider, with licence notes:

| Family | Licence (check each model card) | Note for Dust |
|---|---|---|
| Qwen (Alibaba) | Mostly Apache-2.0; some sizes in some generations shipped under a separate Qwen licence | Strong multilingual; check the exact size |
| Gemma (Google) | Gemma 4 announced under Apache-2.0; earlier Gemma under Gemma Terms of Use with a prohibited-use policy | Earlier terms flow down to derivatives |
| Llama (Meta) | Llama Community Licence: acceptable-use policy, attribution, a large-company threshold | Usable, but not "open source" in the OSI sense; adapters inherit terms |
| Mistral | Many models Apache-2.0; some under research or commercial licences | Check per model |
| Phi (Microsoft) | MIT for recent small models | Good for the small tier |
| OLMo (Ai2), SmolLM (Hugging Face) | Apache-2.0, with open data and training code | Best for fully reproducible research |

**Licence rule for Dust's own releases:** default tiers use bases under Apache-2.0, MIT or
an equivalent licence that allows modification and redistribution without field-of-use
restrictions. An adapter is a derivative of its base; it is published only where the
base licence allows, and the base model's licence and notices travel with it.

## What is downloadable today

* The layer itself (`pip install` from this repository): code, Creed data, constitution
  and the int8 guard weights (`src/dust/data/guard-v0.npz`, 197 KB, Apache-2.0, trained
  only on the synthetic data in this repository).
* No LoRA adapters yet. When one is trained it will be published as a small file next to
  a pinned base model revision, with its evaluation, either in this repository's releases
  or as a Hugging Face draft for Daniel to publish.

## Picking a tier at runtime

The router idea from Always ADR 0015 carries over: pick the tier by device memory,
language and task, and let the person override. A sketch, by free memory: under 6 GB
choose pocket, under 12 GB small, under 24 GB base, otherwise large. Prefer a model that
scores better on the benchmark in the user's language over a bigger one that does not.
