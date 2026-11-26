# Lineage: Rejoice, Always Foundation and Dust

**Dust is a personal research project led by Daniel Dizon and incubated by Rejoice**, a
Christian technology company that invests in, operates and builds for the faith and
flourishing ecosystem. It continues research begun at **Always Foundation**, where Daniel
is a founding contributor.

## What came from Always Foundation

Always Foundation designed *Always AI*: free, private Christian AI infrastructure with the
Nicene Creed of 381 as its only theological boundary (ADRs 0015-0018, an Always AI research
paper and a position paper on Christian AI alignment, November 2026). It published 14 Creed
propositions, 5 excluded historic errors, an assistant specification, an offline Scripture
server, a model recommendation set and a design for end-to-end encrypted private sync. On
25 November 2026 Always decided not to offer Always AI as a product and to leave AI
products to builders, keeping the research published.

Dust picks up from there. From Always it takes, with credit and under CC BY 4.0: the choice
and rationale of the boundary, the propositions and errors (extended), parts of the
assistant instructions (as the constitution), the "least to most invasive" alignment
pathway, the infrastructure-not-companion scope, the model tiers and the private-sync
design.

## What Dust adds

* A machine-checkable encoding of the Creed: 24 atomic propositions with logical literals
  and Greek anchors, 16 excluded errors, 11 latitude topics, 16 inference rules.
* A working layer: symbolic checker with proofs, a shipped neural guard, retrieval, a
  generate-check-repair loop, an OpenAI-compatible HTTP API and a CLI.
* The first measured results for Creed checking: a 307-item hand-labelled benchmark in
  seven languages with a held-out test split, baselines, and every error published.
  (Always's evaluation had been designed but not yet run.)
* The model-family framing, training recipes, and write-ups on open models, hardware,
  privacy and access in hard places.

No Always code is copied: Always's code is TypeScript for a different runtime, and Dust is
written from scratch in Python. No proprietary material is used.
