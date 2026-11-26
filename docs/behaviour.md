# How Dust behaves

Dust sits between a language model and the person using it. The model writes an answer;
Dust reads it, sentence by sentence, before anyone sees it. For each sentence it asks one
question: **does this say, as the speaker's own claim, something the Nicene Creed of 381
rules out?**

Describing a heresy is fine ("Arius taught that the Son was created"). Asserting it is what
Dust looks for ("the Son was created").

## When an answer crosses the boundary

What happens next depends on the behaviour the app chooses. The default is **enforce**.

| Behaviour | What the person receives | Good for |
|---|---|---|
| **enforce** (default) | A rewritten answer, or, if every rewrite still crosses the boundary, a short reply giving what the Creed confesses on that point with Scripture references | Study apps, church tools, anything used by the public |
| **annotate** | The model's own answer, unchanged, plus a verdict (pass, flag or block) with reasons | Review tools, researchers, apps that decide for themselves what to show |
| **explain** | The model's own answer, with a short note at the end naming the article it conflicts with and what the Creed confesses | Teaching settings, where seeing the mistake is useful |

In **enforce** mode, step by step:

1. **Check.** Every sentence is checked against 24 propositions drawn from the Creed.
2. **Rewrite.** If a sentence crosses the boundary and the rules can show which article it
   breaks, Dust sends the answer back to the model with a note quoting that article (for
   example "begotten, not made") and asks for a rewrite. Up to two rewrites.
3. **Refuse with an explanation.** If every attempt still crosses the boundary, the model's
   answer is withheld. The person gets what the Creed confesses on that point, with
   Scripture references, and an offer to explain the history of the question.
4. **Flag when unsure.** When only the learned check is suspicious and the rules cannot
   show a broken article, Dust asks for one gentle rewrite at most and otherwise lets the
   answer through, marked as flagged. A suspicion alone never causes a refusal.

Every answer carries its verdict and the reasons, in every behaviour, so an app can show,
label or log it.

## Questions the Creed leaves open

The Filioque, infant baptism, the Eucharist, church government, Mary, evolution, the end
times, spiritual gifts and similar questions divide faithful Christians, and the Creed of
381 does not settle them. Dust expects the model to present the main traditions fairly. If
an answer claims that the Creed settles one of these questions, that is flagged. If an
answer claims the Creed is silent on something it does settle (for example, whether the
Son was created), that is treated as crossing the boundary and rewritten.

## Denominations and confession profiles

A church or denomination can stack its own confession on top of the Creed as a profile.
The repository includes one for the councils of Ephesus (431) and Chalcedon (451). A profile
can add articles and excluded errors for that deployment; it cannot remove or redefine
anything in the 381 core. Each deployment reports a fingerprint of the boundary it enforces,
so anyone can see which profile is in use.

## Current limits

* **Languages.** The rules read English, and Spanish, Portuguese and German through a
  small phrase pivot that turns the key words into English first. The pivot is new and
  only checked on sentences it was written from, so treat those three as early. In other
  languages only the learned check runs, and it may flag but not block. In three runs on
  small open models, raw answers crossed the boundary in 25 of 150 cases; through Dust,
  6 did, all in German or Spanish. The pivot catches the key sentences from several of
  those leaks when checked on their own; it has not yet been re-run end to end.
* **Evidence.** Those runs used 25 questions, read by one person, and Dust was tuned on the
  same questions. A fresh question set is being written for the next measurement.
* **Review.** The encoding of the Creed has not yet been reviewed by theologians from
  several traditions.

Details: [findings.md](findings.md), [evaluation.md](evaluation.md) and the run reviews in
`results/e2e/`.

## For developers

```python
from dust import Layer
model = Layer().wrap(my_backend, behaviour="enforce")   # or "annotate", "explain"
reply = model.chat([{"role": "user", "content": "Was Jesus created?"}])
reply.content, reply.verdict.decision, reply.refused
```

Over HTTP, add `"dust": {"behaviour": "annotate"}` to an OpenAI-style
`/v1/chat/completions` request. For structured findings without generation, see
[evaluate-api.md](evaluate-api.md).
