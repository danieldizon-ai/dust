# Methods: how to add a doctrinal layer to a model that is already aligned

Every open model arrives aligned to its maker's specification: a model spec, a
constitution, safety tuning and a licence with a use policy. Those specifications are
written for a general public and usually leave doctrine to whoever deploys the model.
Dust adds one more layer on top. It cannot remove what the maker trained in; it can only
add constraints and measure whether they hold. Where the maker's specification and the
Creed pull in different directions, the evaluation should show it rather than anyone
assuming it.

This document compares the ways to add such a layer, says which ones Dust implements in
v0.1, and gives the measured result where there is one.

## Summary

| Method | Changes weights? | Cost to apply | Strengths | Weaknesses | In Dust v0.1 |
|---|---|---|---|---|---|
| System prompt / constitution | No | Zero | Readable, model-agnostic, editable by a church | Small models ignore parts of it; can be overridden by users | Yes: `constitution.md` + full Creed in every request |
| Retrieval (RAG) | No | Very low | Puts the exact relevant article and verses in front of the model; reduces invented quotations | Only helps if the model uses the context | Yes: BM25 over propositions, top 3 articles + WEB verses |
| Output checker: rules / symbolic | No | Low CPU | Precise, explainable (proofs cite the article), no training data | Brittle to paraphrase; English-only patterns | Yes: 90 patterns, 16 rules |
| Output checker: classifier / guard model | No (separate model) | Low to moderate | Generalises to paraphrase | Needs labelled data; opaque; false positives | Yes: 197 KB hashed n-gram guard; transformer guard is future work |
| Scripture reference check | No | Negligible | Catches invented references and, with a Bible text, misquotes | English book names; versification differs slightly between translations | Yes (v0.2): flags, does not block |
| Generate-check-repair loop | No | 1-3x generation | Turns detections into better answers instead of refusals | Latency; a weak model may not repair | Yes: up to 2 repairs, then a cited fallback |
| Supervised fine-tuning / LoRA | Yes (adapter) | GPU hours | Fixes knowledge gaps in small models; adapters are small and shareable | Needs curated data; can damage other skills; licence must allow derivatives | Recipe only (`training/lora_dpo.py`), not run |
| Preference tuning (DPO, constitutional AI / RLAIF) | Yes | GPU hours to days | Shapes default behaviour, not just facts | Data quality dominates; reward hacking; needs multi-tradition review | Seed pairs (`data/dpo_pairs.jsonl`, 48 pairs) + recipe, not run |
| Constrained decoding | No | Low per token | Can forbid exact strings or force a format | Doctrine is about meaning, not tokens: easy to evade, easy to over-block | Not implemented (see below) |
| Neurosymbolic dual track | No | Low | Proofs, model-agnostic, extensible | Formalising natural language is the hard part | Yes, in the practical form described below |

The ordering follows Always Foundation's "least to most invasive" principle (ADR 0015,
point 11): instructions, retrieval and checking first, because they are transparent and
work with any model; training only where the evaluation shows the earlier stages fall
short.

## 1. System prompts and constitutions

The whole Creed is short enough to carry in every request, so Dust always does. The
constitution (`src/dust/data/constitution.md`) adds nine rules: affirm the Creed plainly,
do not assert what it excludes, describing is not asserting, be fair beyond the Creed,
treat the Filioque as an intra-orthodox difference, never invent Scripture, be honest
about uncertainty and authority, hand crisis to people, answer in the user's language.

The same document doubles as the "constitution" for preference training in the style of
constitutional AI (Bai et al., 2022): it is the set of principles a judge model would use
to critique and rank answers.

*Trade-off.* Free and legible, but instructions are suggestions. Small models drift from
them, and a user can ask the model to role-play. That is why Dust checks outputs.

## 2. Retrieval

`dust/rag.py` ranks the 24 propositions against the user's question (BM25 with cue words
per article) and puts the top three, with two verses each, into the system prompt. It
runs in microseconds and needs no embedding model. Larger deployments should add a
proper Scripture retriever; the companion dataset `web-bible-rag` (World English Bible,
CC0, passage-level) is built for that.

## 3. Output checking: the dual track

Dust checks every sentence of a draft answer with two independent tracks.

**Symbolic track** (`dust/symbolic.py`). Text is normalised (the persons of the Trinity
become entity tokens: "the Holy Ghost" -> SPIRIT, "Jesus Christ" -> SON), each sentence
gets a *stance* (the speaker's own assertion, a rejection such as "it is false that ...",
a reported view such as "Arius taught that ...", a question or a hypothetical), and claim
patterns extract logical literals such as `created(SON)` or `-rose(SON)`. Negators between
subject and predicate flip the literal; a contrastive conjunction ("but", "rather")
resets the count. Asserted literals are closed under 16 inference rules (for example
`angel(SON) -> created(SON) -> -eternal(SON)`), and any derived literal whose negation is
an axiom of the Creed is a contradiction, reported with its proof:

```
claim: "SON is the archangel michael" => angel(SON)
R01: angel(SON) -> created(SON) (An angel is a creature.)
contradicts P05 (-created(SON)): The Son is begotten, not made: he is not a creature.
```

**Neural track** (`dust/neural.py`). A linear classifier over hashed word and character
n-grams (2^18 buckets, softmax, int8 weights, 197 KB) predicts contradicts / consistent /
neutral, and a second head guesses which article is concerned.

**Fusion.** The symbolic track always wins where it has something to say: a proof blocks,
and an asserted claim that is *consistent* closes the gate on the neural track for that
sentence. The neural track may block only (a) on sentences the parser read as the
speaker's own assertion but could not parse, (b) that contain doctrinal content, and
(c) in languages it was trained and evaluated in (English, Spanish, Portuguese).
Elsewhere it can only flag for review.

This is the practical form of the neurosymbolic idea, and the benchmark shows why both
tracks are needed (held-out test split, n=153):

| | precision | recall | F1 | false-positive rate |
|---|---|---|---|---|
| keyword baseline | 0.545 | 0.203 | 0.296 | 0.106 |
| symbolic only | 0.971 | 0.576 | 0.723 | 0.011 |
| neural only | 0.806 | 0.424 | 0.556 | 0.064 |
| **dual (Dust)** | **0.930** | **0.678** | **0.784** | **0.032** |

The symbolic track is nearly always right when it fires but misses most paraphrases. The
neural track catches paraphrase but over-blocks negations, reported speech and, as the
first real-model run showed, ordinary assistant prose. Gating the neural track by the
parser's stance and claims keeps most of the recall and removes most of the false
positives. Since v0.3 the generation loop only **refuses** on a symbolic proof; a draft
that only the guard objects to is returned with a flag. Full results, per category and language, and every error
are in `results/benchmark.md`; the method and its limits are in `docs/evaluation.md`.

## 4. The neurosymbolic route, and where it stops being practical

The ambitious version, modelled on AlphaGeometry (Trinh et al., *Nature* 2024), would pair
a neural model that proposes with a symbolic engine that deduces. In AlphaGeometry the
language model proposes auxiliary constructions and a symbolic deduction engine closes the
proof; the symbolic side is complete and sound for its domain because Euclidean geometry
is formalised.

The analogy holds in shape and fails in one crucial place: **doctrine is not formalised the
way geometry is**, and the input is natural language, not a formal problem statement.
Concretely:

* **Formalising the Creed is feasible.** Two dozen propositions and a few dozen rules cover
  the content of 381 and the errors its council named. This repository does it.
* **Formalising arbitrary model output is the bottleneck.** Mapping free text onto
  literals is semantic parsing. Patterns are precise but cover 44% of the contradictions
  in the held-out test set; the rest are paraphrases ("the Spirit is an it"), analogies
  ("one actor playing three parts"), irony, or several sentences that only add up to a
  denial together.
* **Full logical closure is overkill.** The inference needed here is shallow (chains of
  one to three rules). A theorem prover would add little beyond what forward chaining
  already does.
* **Modal and historical nuance resists formalisation.** "Jesus is a god", "Jesus is God",
  "Jesus became God", "Jesus was God's agent" differ in exactly the ways the fourth century
  fought about. A formal language rich enough to tell them apart (with time, modality,
  attribution and degree) would need a far larger parser.

So Dust uses neurosymbolic methods where they pay: the symbolic side guarantees an
explanation for every block it causes and decides stance (assertion versus report), and
the neural side covers paraphrase. The natural next step is to let a small language model
do the semantic parsing (text -> literals, constrained to the literal vocabulary) and keep
the rule engine for checking. That is closer to the AlphaGeometry split, and it is
promising because the target vocabulary is tiny; it needs a model in the loop and was out
of reach in the sandbox that built v0.1.

## 5. Guard models

A guard model is a second, small model that classifies inputs or outputs against a policy
(Llama Guard is the best-known open example; Inan et al., 2023). Dust's v0 guard is a
deliberately small linear model so that it ships inside the package, runs in about a
millisecond on a CPU and makes its limits obvious. A transformer guard (for example a
fine-tuned small encoder, or a 0.5-1B decoder prompted with the propositions) should
generalise much better to paraphrase and other languages. It needs (a) more and better
labelled data than the synthetic set here, ideally reviewed by people from several
traditions, and (b) compute to train and evaluate. The benchmark harness is ready for it:
any object with `scores(text)` can be plugged into `Layer`.

## 6. Fine-tuning: LoRA, SFT, DPO

When instructions and checking are not enough, usually because a small model lacks the
knowledge or keeps drifting, train an adapter.

* **LoRA** (Hu et al., 2021) trains small low-rank matrices beside frozen weights. Adapters
  are megabytes, cheap to train and easy to distribute next to a base model whose licence
  allows it. Thinking Machines Lab's "LoRA Without Regret" (Schulman et al., 2025) reports
  that LoRA matches full fine-tuning in many post-training settings when applied to all
  layers with a suitable learning rate, which supports the adapter route for a project
  this size.
* **DPO** (Rafailov et al., 2023) trains directly on pairs of better and worse answers
  without a separate reward model. `training/dpo_pairs.py` builds 48 seed pairs from the
  knowledge base (each excluded error, answered faithfully versus asserted), and
  `training/lora_dpo.py` is a TRL + PEFT recipe. Neither has been run: the sandbox had no
  GPU and no access to model weights. Seed pairs written by one person are not a
  preference dataset; real pairs need multi-tradition review.
* **Constitutional AI / RLAIF** (Bai et al., 2022): a judge model critiques drafts against
  the constitution and the critiques become preference data. Feasible for open models;
  the judge should not be the model under test.

*Risks.* Fine-tuning can erode other capabilities and the maker's safety tuning; it can
teach a model to *sound* creedal rather than reason carefully; and an adapter is a
derivative work, so the base model's licence governs whether it can be shared (see
`docs/model-family.md`). Measure before and after with `bench/e2e.py`.

## 7. Constrained decoding

Constrained decoding masks tokens during generation, for example to forbid exact strings
or force a JSON schema. It is excellent for format and useless as the main doctrinal
control: forbidding "created being" does not stop "brought into existence by the Father",
and forbidding "created" at all would stop the model saying "begotten, not created". Dust
does not implement it. One sensible use is structural: force the model to emit
`{"answer": ..., "citations": [...]}` so references can be verified mechanically.

## References

* Trinh, Wu, Le, He, Luong. "Solving olympiad geometry without human demonstrations."
  *Nature* 625 (2024).
* Bai et al. "Constitutional AI: Harmlessness from AI Feedback." arXiv:2212.08073 (2022).
* Rafailov et al. "Direct Preference Optimization." arXiv:2305.18290 (2023).
* Hu et al. "LoRA: Low-Rank Adaptation of Large Language Models." arXiv:2106.09685 (2021).
* Schulman and Thinking Machines Lab. "LoRA Without Regret." thinkingmachines.ai (2025).
* Inan et al. "Llama Guard." arXiv:2312.06674 (2023).
* Always Foundation. ADR 0015 and the position paper on Christian AI alignment (2026).
