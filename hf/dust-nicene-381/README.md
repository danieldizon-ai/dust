---
license: cc-by-4.0
language:
- en
- es
- fr
- pt
- de
- tl
- id
pretty_name: Dust Nicene 381 boundary and test set
task_categories:
- text-classification
tags:
- alignment
- theology
- christianity
- nicene-creed
- evaluation
size_categories:
- n<1K
configs:
- config_name: claims
  data_files:
  - split: test
    path: claims/test.jsonl
  - split: dev
    path: claims/dev.jsonl
- config_name: questions
  data_files:
  - split: v0
    path: questions/v0.jsonl
- config_name: propositions
  data_files: boundary/propositions.jsonl
- config_name: excluded_errors
  data_files: boundary/excluded_errors.jsonl
- config_name: latitude
  data_files: boundary/latitude.jsonl
- config_name: profiles
  data_files: profiles/profiles.jsonl
---

# Dust: the Nicene Creed (381) as a machine-checkable boundary, with a test set

This is the data behind [Dust](https://github.com/DanielDizon-AI/dust), an open alignment
layer that keeps any open language model inside the Nicene Creed of 381 while leaving
open what the Creed leaves open. It is published so that others can test their own
models and checkers against the same boundary, extend it, or fork it for their own
tradition.

Led by Daniel Dizon, incubated by Rejoice, building on research by Always Foundation.

## What is in it

| Config | Rows | What it is |
|---|---|---|
| `claims` | 153 test, 154 dev | Hand-labelled sentences: does this sentence, as the speaker's own view, assert something the Creed excludes (`contradicts`), affirm it (`consistent`), or neither (`neutral`: reported views, questions, open questions, off-topic). Seven languages; categories include direct, paraphrase, negation, reported speech, adversarial wording, multi-sentence and latitude |
| `questions` | 25 | The prompts used in Dust's end-to-end runs on real models. **No longer unseen**: Dust's checker was tuned after reading model answers to them |
| `propositions` | 24 | The Creed split into atomic propositions, each with a logical literal, the Greek text it rests on and Scripture references |
| `excluded_errors` | 16 | Positions the Creed excludes (Arianism, modalism, docetism ...), with the propositions each contradicts and where it was condemned |
| `latitude` | 11 | Questions the Creed of 381 leaves open between Christian traditions (the Filioque, baptism, church order ...), which a model must present fairly rather than decide |
| `profiles` | 1 | Confession profiles that stack on top of the Nicene boundary. The included example adds Ephesus (431) and Chalcedon (451) and is written so that it leaves the Miaphysite formula inside |

## How to use it

```python
from datasets import load_dataset
test = load_dataset("danieldizon/dust-nicene-381", "claims", split="test")
```

Score a checker on `claims/test` with `contradicts` as the positive class. Dust's own
results on this split (precision 0.925, recall 0.627, F1 0.747, false-positive rate 3.2%)
and every error it makes are in the repository under `results/benchmark.md`. Please
report false-positive rate as well as recall: in Dust's own runs on real models, wrongly
refusing good answers was the dominant failure.

To make a profile for your tradition, copy `profiles` and add propositions and excluded
errors. A profile may only add to the Nicene boundary; it cannot redefine it.

## Limits

* One author wrote the propositions, the labels and the training generator. No panel from
  Catholic, Orthodox, Oriental Orthodox and Protestant traditions has reviewed it yet.
* The test split is small (about plus or minus 0.07 on precision and recall) and mostly
  English; the six other languages have 6 to 8 items each.
* The labels judge one thing only: whether a sentence asserts a position the Creed of 381
  excludes. They say nothing about whether an answer is good, kind or complete.

## Licence and attribution

CC BY 4.0. The propositions and excluded errors are adapted and extended from Always
Foundation's `nicene-381.json` (CC BY 4.0): the original 14 propositions were split into
atomic propositions with literals, Greek anchors and Scripture references, and the 5
excluded errors were extended. The English Creed text is a public-domain translation.
The Always name is a trademark of Always Foundation and does not brand this dataset.
