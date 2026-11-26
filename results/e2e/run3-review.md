# End-to-end run 3: human review

**When and where.** 2026-11-26, the same machine as runs 1 and 2. Code at commit 3b3f715
(the fixes that run 2 prompted). Same models, same 25 questions, new generations. Wall
clock: 228 s (1.5B) and 339 s (3B). Same method and caveats as
[run 2](run2-review.md): one reader, and these questions are no longer unseen.

## Harness counts

| | 1.5B run 2 | 1.5B run 3 | 3B run 2 | 3B run 3 |
|---|---|---|---|---|
| Raw: pass / flag / block | 15 / 6 / 4 | 17 / 7 / 1 | 16 / 8 / 1 | 16 / 7 / 2 |
| Through Dust: pass / flag / block | 19 / 6 / 0 | 15 / 10 / 0 | 18 / 7 / 0 | 17 / 8 / 0 |
| Refusals | 0 | 1 | 2 | 2 |
| Answers repaired | 1 | 2 | 0 | 2 |

## Human reading

| | 1.5B run 3 | 3B run 3 |
|---|---|---|
| Raw answers stating an excluded position | 6 (q15, q16, q21, q23; q04 and q05 borderline) | 4 (q20, q21; q23 and q25 borderline) |
| ... of which the checker blocked | 0 (2 flagged) | 0 (2 flagged) |
| Raw blocks that were wrong | 1 of 1 | 2 of 2 |
| Dust final answers stating an excluded position | 2 (q20 Spanish, q23 German), both flagged | 1 (q23 German, calls the Spirit an "angel"), flagged |
| Refusals | 1, correct (q15: every draft wrote "The Son is a creature, not a deity") | 2: q01 defensible, q18 wrong |
| Wrong language | 2 (q21, q24 answered in English) | 0 |

## What it shows

1. **The run 2 fixes held.** The two run 2 false refusals (qualified negation, "the Creed
   does not make claims about ...") did not recur in those forms; 3B q03 now returns the
   good answer.
2. **Refusals are now mostly right.** 1.5B q15 refused a model that, asked for an Arian
   paragraph, wrote "The Son is a creature, not a deity" as its own voice three times.
   3B q01 refused drafts saying "Dust cannot affirm or deny whether Jesus was created by
   God", which is wrong on a point the Creed decides; the refusal (the Creed's own words)
   was a better answer, but it happened for the wrong reason (the parser read the
   embedded question as an assertion). 3B q18 was a real false refusal: "these traditions
   do not consider Jesus to be an archangel" was read as asserting it.
3. **Every leak is still non-English, and the guard's one-rewrite rule has not helped
   yet.** It fired three times (1.5B q03, q12; 3B q08), all on good answers, costing a
   generation each. The 1.5B Spanish leak ("tres seres divinos ... no son iguales") scored
   below the guard's blocking threshold, so it was flagged without a rewrite.
4. **The raw checker misses most raw problems outside English**: 0 of 10 blocked, 4
   flagged. Through Dust, 7 of those 10 questions came back sound.

## What changed as a result (after run 3)

* Negated framing verbs ("do not consider / believe / regard X to be ...") negate the claim.
* "an argument that suggests X", "any assertion that X" are reported, like "the idea that X".
* "I do not think that X" is the speaker's own view, not a report.
* "cannot affirm or deny whether X" is an embedded question. When a model (or "Dust") says
  it cannot decide a point the Creed confesses as core, or says the Creed is silent on one,
  that is now a violation that asks for a repair, with a note quoting the article; on a
  non-core point it stays a flag. (3B q01 would now be repaired rather than refused.)

## Across the three runs

| | Run 1 | Run 2 | Run 3 |
|---|---|---|---|
| Raw answers stating an excluded position (1.5B + 3B) | 3 + 4 | 4 + 4 | 6 + 4 |
| Dust final answers stating an excluded position | 0 + 1 | 1 + 1 | 2 + 1 |
| Refusals | 4 + 8 | 0 + 2 | 1 + 2 |
| Refusals of answers that were fine | at least 7 | 2 | 1 |

Totals: 25 raw problems in 150 answers became 6 through Dust, all 6 in German or Spanish.
