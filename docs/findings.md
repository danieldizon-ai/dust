# Findings and conclusion

This is the summary of what Dust v0.1-v0.3 set out to test, what was built, what the
measurements show, what we learned, and where the approach falls short. The roadmap that
follows from it is in [roadmap.md](roadmap.md).

## The question

Can a Christian doctrinal boundary, the Nicene Creed of 381, be added as a separate,
transparent layer on top of any open model (which already carries its maker's own
alignment), in a way that is free, private, runs on ordinary hardware, and can be
measured rather than asserted?

## Short answer

**Partly, and the measurable part works better than expected for its size.** A layer of
under 1 MB that runs in about half a millisecond per sentence on a CPU can tell, with
about 87% precision, when a text asserts something the Creed excludes. It catches about
70% of such assertions on unseen test sentences (86% in English across all items), and it
almost never blocks history, questions or legitimate differences between traditions. It
explains every rule-based block with a proof that cites the article of the Creed.

What it has **not** shown yet is the thing that matters most: whether wrapping a real
small model in this layer produces better answers. That needs a model run, which the
sandbox could not do. Everything here is the checker and the scaffolding around it.

## What was built

| Component | State |
|---|---|
| The Creed as data: 24 propositions (Greek anchors, Scripture), 16 excluded errors, 11 latitude topics, 16 rules | Done; adapted from Always Foundation and extended |
| Symbolic checker with stance detection and proofs | Done; English |
| Neural guard (hashed n-grams, int8, 197 KB) | Done; trained on synthetic data |
| Dual-track fusion with stance gate and language restriction | Done |
| Constitution, retrieval of relevant articles and verses, generate-check-repair loop | Done; repair loop tested with scripted models only |
| Scripture reference checker (invented references, misquotes) | Done (v0.2) |
| Confession extensions (stack Chalcedon or a church's statement on top) | Done (v0.2) |
| Input hardening against look-alike letters, invisible characters, spaced letters | Done (v0.3) |
| Boundary audit (consistency, every error excluded, grounding) and fingerprint | Done (v0.3) |
| Dust Study: a minimal local study page; Ollama Modelfile generator | Done (v0.3) |
| OpenAI-compatible HTTP API, CLI, Python package | Done |
| Benchmark (307 items, 7 languages, held-out test split), ablation study | Done |
| End-to-end evaluation on real models | Script ready; not run |
| LoRA / DPO adapters | Seed data and recipe; not run |

## Methods compared

What could be measured without a model is the checking stage. Held-out test split
(n = 153), positive class = the text asserts an excluded position.

| Method | Precision | Recall | F1 | False-positive rate | Notes |
|---|---|---|---|---|---|
| Keyword list | 0.545 | 0.203 | 0.296 | 0.106 | What many "guardrails" start as. Blocks "Arius taught that the Son was created" and misses nearly everything else |
| Symbolic rules only | 0.963 | 0.441 | 0.605 | 0.011 | Almost never wrong; misses most paraphrase |
| Neural guard only | 0.733 | 0.559 | 0.635 | 0.128 | Catches paraphrase; reads "not", "never" and reported speech as heresy |
| **Dual track (Dust)** | **0.872** | **0.695** | **0.774** | **0.064** | Symbolic proof first; neural only where the parser says the sentence is the speaker's own assertion and could not parse it |

Methods that change the model (system prompt, retrieval, LoRA, DPO) could not be compared
here because no model could be run. `bench/e2e.py` is the harness for that comparison:
same 25 questions, raw model versus Dust-wrapped, with every transcript saved.

## What we learned

**1. The two tracks fail in opposite ways, which is why combining them works.** Rules are
precise and brittle; the learned guard generalises and over-reaches. Neither alone gets
above F1 0.64; together they reach 0.77. Neurosymbolic is the right shape for this problem,
even though full formalisation is not practical.

**2. Stance matters more than content.** The single most important design decision was
separating *saying* from *describing*. Without the stance gate, false positives more than
double (6.4% to 14.9% on test) because the guard blocks history, questions and negated
affirmations. A doctrinal layer for a study tool has to let a model explain Arius
accurately; a naive filter cannot.

**3. Shallow inference earns its keep.** Removing the 16 rules drops test recall from
0.70 to 0.49. Much of what models actually say ("Jesus is an angel", "the Spirit is a
force", "he was only a prophet") contradicts the Creed only after one step of reasoning
(an angel is a creature, a creature is not eternal). The chains are short (one to three
steps); a full theorem prover would add little.

**4. The boundary itself held up under testing.** The 42 latitude statements (both sides of
baptism, the Eucharist, the papacy, the Filioque, justification, purgatory, creation and
evolution, the millennium, women's ordination) were blocked only twice (4.8%). Choosing
381 rather than a confession makes the layer genuinely neutral between traditions while
staying firm on the doctrine of God. The Chalcedon extension shows the stack works: a
church can add more without changing the default for everyone else.

**5. Data is the bottleneck, not model size.** Halving the training data costs the guard
recall; character versus word features and entity normalisation each move F1 by only
0.02-0.03 in the dual system. A 197 KB linear model is good enough as a fallback because
the rules do the precise work. Better labelled data, written by more people, would help
more than a bigger classifier trained on the same data.

**6. Our own fixes cost recall.** The second iteration (informed only by the dev split)
halved false positives on the test split (12.8% to 6.4%) and lost recall (0.81 to 0.70).
Part of that was a deliberate policy: outside English, Spanish and Portuguese, the guard may
only flag, not block. The ablation shows that on this small sample the restriction cost a
little recall without buying precision (F1 0.785 without it). We kept it anyway, because
4-8 items per language cannot validate blocking in that language. That is a judgement,
not a measurement, and it is the kind of choice a deployment should make explicitly.

**7. Multilingual is the weakest point, and it matters most.** German, Tagalog and
Indonesian contradictions are largely missed. The places where access to faithful,
private tools is hardest are often the languages where small models and open Bibles are
weakest. Pivot translation through English is implemented as a hook but untested.

**8. Cheap evasions work on unhardened checkers, and cheap fixes stop them.** Without
input hardening, writing a contradiction in full-width characters got every one of 85
past the checker; zero-width characters got half past. Canonicalising the text first (NFKC,
invisible characters removed, look-alikes mapped back only inside mixed-script words)
restores 100% on all four evasions without touching Greek or Russian text or changing a
single benchmark count. Any doctrinal or safety filter that matches text should do this.

**9. The encoding can be checked, not just the checker.** Closing the Creed's own literals
under the rules shows the boundary is consistent, and every one of the 16 excluded errors
is in fact excluded by the propositions it is recorded as denying. The audit also showed
four articles (the incarnation "for our salvation", the ascension, the procession of the
Spirit, and "spoke through the prophets") that no recorded error touches; they rely on
claim patterns alone and need more test items.

**10. Measuring honestly changes the story.** The first run looked better on recall than the
final one. Keeping first-run numbers, a dev/test split, overlap reports and a CI check
that fails if any count changes makes the results believable, including the bad ones.

## Where the approach falls short

* **No end-to-end evidence.** The checker is measured; the effect on a real model's answers
  is not.
* **One author.** The same person wrote the propositions, the training generator and the
  test set. No theologians from Catholic, Orthodox and Protestant traditions have reviewed
  the encoding; no inter-annotator agreement exists.
* **Small test set.** 153 items give roughly plus or minus 0.07 on precision and recall.
* **Paraphrase and long arguments.** Recall on indirect wording is 0.64; denials spread
  across several sentences, irony and analogies still get through.
* **English-only rules.** The symbolic track does not read other languages.
* **Pronoun and context heuristics.** An unresolved "he" is assumed to be the Son;
  sentence-level checking misses context.
* **A checker is not wisdom.** It tests statements against propositions. It cannot judge
  pastoral fit, tone or whether an answer is helpful, and it must never be presented as a
  spiritual authority.
* **Forks can remove it.** Open code can be stripped of the layer; only measurement and a
  maintained reference version protect users.

## Conclusion

A Nicene layer is technically feasible, cheap enough to run anywhere, and can be honest
about its own limits. The neurosymbolic split (rules for proof and stance, learned models
for coverage) is the right architecture. The Creed of 381 is a workable boundary: firm on
God, Christ and the Spirit, and fair on everything the traditions still debate. What
remains is the part that turns a promising checker into trustworthy infrastructure: run it
on real models, have it reviewed by people from several traditions, replace the
hand-written patterns with a small-model parser, and extend it to the languages that need
it most. [roadmap.md](roadmap.md) sets out how.
