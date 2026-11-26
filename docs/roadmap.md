# Research roadmap

Concrete next steps for whoever takes Dust forward, in priority order. Each item says what
to do, how to know it worked, and what it needs. Items in the same phase can run in
parallel.

## Phase 1: evidence (weeks)

### 1.1 Run the full loop on real models
* **Do:** run `bench/e2e.py` on the family's base models (start with a 1-2B, a 3-4B and an
  8-12B Apache-2.0 model through Ollama or llama.cpp). Then expand `data/eval/questions-v0.jsonl`
  from 25 to about 200 questions across the latitude topics, adversarial prompts and the
  seven languages.
* **Measure:** for each model, raw versus Dust: rate of answers with an excluded assertion
  (checker plus human reading of transcripts), repair success rate, refusal rate, latency
  overhead, and helpfulness rated by readers.
* **Done when:** a published scorecard per model, with transcripts.
* **Needs:** one machine that can run the models (a 16-32 GB laptop is enough for the small
  tiers).

### 1.2 Theological review of the encoding
* **Do:** recruit at least one reviewer each from Catholic, Eastern Orthodox, Oriental
  Orthodox and two or more Protestant traditions. Review `creed.json` (propositions, Greek
  anchors, excluded errors, latitude topics), the constitution and a sample of the
  benchmark labels.
* **Done when:** each item is marked agree / amend / disagree with reasons, amendments are
  merged, and the reviewers are credited.
* **Needs:** people, not compute.

### 1.3 An independent evaluation set
* **Do:** have people other than the original author write and label at least 500 new items
  using the categories in `docs/evaluation.md`, with two labellers per item.
* **Measure:** inter-annotator agreement (Cohen's kappa); the current system's scores on
  the new set (expect them to fall).
* **Done when:** the new set replaces v0 as the headline benchmark.

## Phase 2: better checking (one to three months)

### 2.1 A small-model semantic parser (the AlphaGeometry split)
* **Do:** prompt or fine-tune a 0.5-1.5B model to map a sentence to Dust's literal
  vocabulary plus a stance (`{"stance": "assert", "literals": ["created(SON)"]}`), using
  constrained decoding to a JSON schema so it can only emit known literals. Keep the rule
  engine for checking and proofs. Use the current regex parser as a fallback and as a
  source of silver labels.
* **Measure:** parser accuracy on literals; end-to-end F1 against the current dual track.
* **Target:** paraphrase recall above 0.85 at the current precision.

### 2.2 A transformer guard
* **Do:** fine-tune a small multilingual encoder on the training data plus the
  independent set, and plug it into `Layer(guard=...)` (anything with `scores(text)` works).
* **Measure:** neural-only and dual F1, false positives on latitude and reported items.
* **Needs:** a single GPU for hours.

### 2.3 Multilingual
* **Do:** (a) evaluate the pivot-translation hook (`Layer(translate=...)`) with the wrapped
  model doing the translation; (b) machine-translate the training set into the target
  languages and have native speakers review samples; (c) extend the benchmark to at least
  50 items per language for 10 languages, prioritising languages with large Christian
  populations and weak model support (for example Swahili, Amharic, Hausa, Yoruba, Hindi,
  Tagalog, Indonesian, Korean, Chinese, Arabic).
* **Done when:** each released language has its own validated blocking threshold, or is
  marked flag-only.

### 2.4 Context-aware checking
* **Do:** check sentences with their neighbours, resolve pronouns properly, and detect
  denials spread across sentences.

## Phase 3: training (when phase 1 shows the need)

The full catch-up and release pipeline (measure, adapt, distil, quantise, release,
maintain) with compute estimates is in [release-plan.md](release-plan.md).

### 3.1 LoRA adapters per tier
* **Do:** run `training/lora_dpo.py` after replacing the seed pairs with a reviewed
  preference set of at least 1,000 pairs (from phase 1 transcripts: raw answers that
  failed versus repaired or human-written answers).
* **Measure:** before/after on `bench/e2e.py` and on general benchmarks, to catch damage to
  other skills or to the maker's safety tuning.
* **Publish:** only for bases whose licence allows derivatives; as Hugging Face drafts with
  the base revision pinned.

### 3.2 A Nicene constitution for preference training
* **Do:** constitutional-AI style: a judge model (not the model under test) critiques drafts
  against `constitution.md`; critiques become preference data; humans audit a sample.
* **Risk to watch:** models learning to sound creedal rather than to reason carefully.

## Phase 4: infrastructure and access

* **Dust Study:** grow the local study page (`dust serve`, then open the browser) into a
  proper reference app with history kept on the device, Scripture lookup and
  profile selection, or hand that to an app partner and keep Dust as infrastructure.
* **Hardening:** multi-turn and role-play policy, per-language thresholds, signed releases
  with pinned hashes, and test items for the four articles the audit shows are protected by
  patterns only ([hardening.md](hardening.md)).
* **Profiles:** publish two or three real confession profiles with reviewers from those
  traditions (for example a Catechism profile and a Westminster profile), each with its own
  tests and fingerprint.
* **Packaging:** a signed release with model hashes; a Docker image for church servers; a
  browser build of the layer (it is pure Python and numpy today; a port of the checker to
  JavaScript or WebAssembly would let Bible apps run it client-side).
* **Private sync:** implement the vault format and key exchange in `docs/privacy.md`,
  publish the threat model and test vectors, and have it reviewed by a security
  professional before anyone relies on it.
* **Hard places:** an offline bundle (pocket model, layer, Bible) under 2 GB with
  verification instructions, designed with partners who work in those contexts.
* **SDKs:** thin clients for the HTTP API in TypeScript, Swift and Kotlin.

## Open research questions

1. When an open model's maker specification and the Creed pull in different directions
   (for example, a default to present all religious claims as equally valid), which wins
   in practice, at which model sizes, and can a layer move it?
2. Does checking plus repair beat fine-tuning for small models, or do they compound?
3. How much doctrinal faithfulness survives distillation and 4-bit quantisation? Compare
   the same family at 16, 8 and 4 bits.
4. Can the propositional encoding be generalised so that any confession (Westminster, the
   Catechism, an Orthodox catechism, a church's statement of faith) is an extension file,
   with automatic test generation?
5. What is the right behaviour for questions where a tradition's own teaching goes beyond
   the Creed? Defer to the user's church library (Always's proposal), present the range, or
   ask?
6. How should a layer like this be governed, so that the boundary stays the Creed and does
   not quietly grow?

## Funding

The expensive part is people (review, independent evaluation, multilingual review), not
compute. Estimates by phase are in [economics.md](economics.md).

## Suggested ownership

Dust is incubated by Rejoice. A sensible split: Rejoice funds and steers; an engineer or
research student takes phase 2; volunteers from several traditions take 1.2 and 1.3;
Always Foundation remains the steward of the research it published and can review
anything that builds on it.
