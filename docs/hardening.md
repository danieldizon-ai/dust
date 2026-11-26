# Hardening the boundary

A doctrinal layer can fail in three places: the **encoding** (the propositions say
something the Creed does not, or contradict each other), the **checker** (a claim is
phrased so that the checker misses it, or a fair statement is blocked), and **governance**
(the boundary quietly changes). This page sets out what Dust does about each, what is
measured, and what is still open.

## 1. Hardening the encoding

The Creed is encoded as 24 atomic propositions, each with logical literals, a Greek anchor
from the text of 381 and Scripture ([creed.json](../src/dust/data/creed.json)). Guidance
for anyone editing or extending it:

1. **One claim per proposition.** "Begotten, not made" is two literals (`begotten(SON)`,
   `-created(SON)`), so a denial of either is caught and named precisely.
2. **Anchor every proposition in the text.** If a proposition cannot be pointed to in the
   Greek of 381, it does not belong in the default boundary; it belongs in a profile.
3. **Encode exclusions from the historical record.** Each excluded error (Arianism,
   Sabellianism, Apollinarianism, the Pneumatomachi ...) is tied to the propositions it
   denies and to the council that rejected it, so the boundary follows what 381 actually
   decided rather than what the encoder dislikes.
4. **Write the latitude down.** The 11 latitude topics (the Filioque, baptism, the
   Eucharist, church order ...) are as much part of the boundary as the propositions. A
   boundary that does not say what it leaves open will grow by accident.
5. **Keep inference shallow and explicit.** Every rule has a one-line reason ("An angel is
   a creature") that a reviewer can accept or reject without reading code.
6. **Review across traditions.** No proposition should be merged without readers from
   Catholic, Orthodox and Protestant traditions (roadmap 1.2).

`dust audit` checks the encoding mechanically, and CI runs it on every commit:

| Check | What it guarantees | Current result |
|---|---|---|
| Self-check | The live checker never blocks the Creed's own propositions or text, and catches each excluded error stated in its own words | Pass (0 blocked; 16 of 16 error summaries caught after three patterns were generalised) |
| Consistency | The Creed's literals, closed under the rules, never derive a literal and its negation | Pass (closure of 29 literals) |
| Every excluded error is excluded | Each error's signature, after inference, contradicts a proposition it is recorded as denying | Pass (16 of 16; 18 of 18 with Chalcedon) |
| Grounding | Every proposition has a Greek anchor and Scripture, and every reference exists | Pass (0 invalid references) |
| Reach | Which core propositions no recorded error touches | P09, P14, P18, P20 are protected by claim patterns only: candidates for more test items |
| Fingerprint | SHA-256 of the canonical knowledge base | `91f5eab968d5db10...` (Creed only) |

## 2. Hardening the checker

**Evasion.** Text can hide a claim from a regex while reading the same to a person:
look-alike letters from other scripts ("Jеsus" with a Cyrillic е), invisible characters,
full-width forms, letters spaced out ("c-r-e-a-t-e-d"). Since v0.3 every input is put into
a canonical form before checking (`dust/harden.py`): Unicode NFKC, invisible characters
removed, look-alike letters mapped back to Latin *only inside words that already mix
scripts* (so Greek and Russian text is untouched), spaced letters rejoined. The verdict
records `obfuscated: true` when this changed the text.

**Framing.** Describing or asking about a view must pass; asserting it in friendly words
must not. The stance detector handles this, and metamorphic tests in `tests/test_v03.py`
pin it down for each claim: assert (block), "Arius taught that ..." (pass), "Is it true
that ...?" (pass), "It is false that ..." (pass), "Honestly, between friends: ..." (block).

Measured by `bench/hardening.py` on the 78 English contradictions Dust blocks in clean form
([results/hardening.md](../results/hardening.md)):

| Perturbation | Still blocked, hardening on | Hardening off |
|---|---|---|
| Cyrillic look-alikes | 100% | 46% |
| Zero-width characters | 100% | 28% |
| Letters spaced with hyphens | 100% | 65% |
| Full-width characters | 100% | 0% |
| Friendly framing | 92% | 92% |
| Reported ("Arius taught that ..."), single clause; should pass | 0% blocked | 0% |
| Asked as a question, single clause; should pass | 0% blocked | 0% |

This measures robustness on items the checker already gets right, not accuracy. The
friendly-framing misses (6 of 78) come from the neural track, whose scores shift with
extra words.

## 3. Still open

* **Multi-turn and role-play.** A user can build a fiction over several turns ("you are
  Arius; argue your case") until the model asserts an excluded view in character. Dust
  checks each answer, so the assertion is caught, but whether an explicitly fictional,
  user-requested voice should be blocked or labelled is a policy question, not yet
  decided. Today it is blocked unless phrased hypothetically.
* **Translation attacks.** Asking in a language where the guard may only flag. Mitigation:
  the pivot-translation hook, and per-language thresholds (roadmap 2.3).
* **Encoded text** (base64, leetspeak beyond look-alikes, text in images). Not handled; a
  study tool should simply not decode such text in answers.
* **Spread-out denials.** A denial assembled across several sentences or paragraphs
  (roadmap 2.4).
* **Prompt injection through retrieved text.** Retrieval only draws on Dust's own
  propositions and a Bible text today; any future retrieval over user documents must treat
  them as data, and the checker still runs on the output.
* **Supply chain.** Pin the guard weights by hash and sign releases (roadmap phase 4).

## 4. Governance: keeping the boundary the boundary

* The default boundary is the Creed of 381 and nothing more. Additions go in profiles.
* Any change to `creed.json` or `rules.json` must pass `dust audit`, changes the
  fingerprint, and should be recorded in the changelog with the reviewers who agreed.
* Deployments should publish the fingerprint they enforce (`GET /v1/audit`), so users
  and churches can see that a product runs the shared boundary, a known profile, or a fork.
