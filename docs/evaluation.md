# Evaluation: method, history and limits

## Task

Given a text, decide whether the speaker *asserts* something the Creed of 381 excludes.
Positive class: `contradicts`. Negative classes: `consistent` (affirmations, and positions
inside the latitude of the Creed) and `neutral` (reported views, history, questions,
off-topic text).

## Data

`data/eval/nicene-eval-v0.jsonl`: 307 hand-written, hand-labelled items, written
separately from the synthetic training data and in different wording.

| Category | n | What it tests |
|---|---|---|
| direct | 45 | Plain statements of an excluded error |
| paraphrase | 25 | The same errors in indirect or figurative wording |
| affirm | 40 | Plain affirmations of the Creed (must pass) |
| latitude | 42 | Positions on which traditions differ, both sides (must pass) |
| reported | 35 | Historical and third-party descriptions of excluded views (must pass) |
| question | 15 | Questions about them (must pass) |
| negation | 25 | Negation and scope traps, both labels |
| adversarial | 15 | Errors wrapped in friendly, "neutral" or analogy framing, and the reverse |
| multi | 15 | Multi-sentence, model-style answers |
| offtopic | 10 | Must pass |
| multilingual | 40 | es, pt, fr, de, tl, id |

The set is split deterministically by a hash of the item id into **dev** (154 items, used
for error analysis) and **test** (153 items, reported). Overlap with training data: 3 exact
duplicates (short canonical sentences such as "Jesus is not God.") and 11 near duplicates
by word 4-gram Jaccard >= 0.5, out of 307.

## History (kept so the numbers can be judged)

1. **First run** (`results/first-run.json`), before looking at any errors. Test split, dual
   track: precision 0.800, recall 0.814, F1 0.807, false-positive rate 0.128.
2. **Iteration 2**, after error analysis on the **dev split only**: more general claim
   patterns (passives with negation, "rather than", body-in-the-tomb), negation-bearing
   consistent sentences and history sentences added to the training generator, a gate so
   the neural track ignores sentences with no doctrinal content, pronouns resolved to the
   previous sentence's subject, and a rule that the guard may only *flag*, not block,
   outside the languages it was trained on. Test items were not inspected.
   Result on the test split: precision 0.872, recall 0.695, F1 0.774, false-positive rate
   0.064.

So iteration 2 halved false positives on unseen data and lost recall, much of it on
purpose (unvalidated languages now flag instead of block). Dev-split numbers after
iteration 2 (F1 0.883) are optimistic because the fixes were made by looking at that split.

## Final numbers (test split, n=153)

| system | precision | recall | F1 | false-positive rate |
|---|---|---|---|---|
| keyword baseline | 0.545 | 0.203 | 0.296 | 0.106 |
| symbolic only | 0.963 | 0.441 | 0.605 | 0.011 |
| neural only | 0.733 | 0.559 | 0.635 | 0.128 |
| **Dust (dual)** | **0.872** | **0.695** | **0.774** | **0.064** |

All items, by category, for the dual track: direct recall 0.89; paraphrase recall 0.64;
adversarial recall 0.90; multi-sentence recall 1.00; false positives 10% on affirmations,
4.8% on latitude, 0% on reported views and questions. English recall 0.85 with 4.2% false
positives. Every individual error is listed in `results/benchmark.md`.

## What these numbers do and do not show

* They measure the **checker**, not a model. No base model was run (the sandbox had no
  access to model weights). `bench/e2e.py` measures the full loop against any
  OpenAI-compatible endpoint and keeps every transcript; it is the next thing to run.
* One author wrote both the training generator and the evaluation set. Different wording
  was used on purpose and overlap is measured, but shared habits of phrasing will still
  flatter the results. An evaluation set written by others, from several traditions, is
  needed before any public claim.
* Labels are one person's judgement. Some items are arguable (for example, whether
  "Jesus was divine only in the sense that we are all divine" is a denial of P06; it is
  labelled as one). Inter-annotator agreement has not been measured.
* 153 test items give wide confidence intervals: roughly plus or minus 0.07 on precision
  and recall.
* The benchmark is reproducible: `python bench/run.py --check` recomputes it and fails if
  any count changes, and CI runs that check.
