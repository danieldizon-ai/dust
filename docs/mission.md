# Mission: free, open, private AI for the global Church

Dust exists to help make one thing possible: **any Christian, in any church, in any
language and in any country, can use a capable AI study tool that is free to use, open to
inspect, private by default, and faithful to the historic faith.**

## Four commitments

| | What it means in practice | Why it matters |
|---|---|---|
| **Free** | No subscription and no per-question cost. Inference runs on hardware people already own, so serving one more person costs the project nothing. | Most Christians live in places where a $20-a-month AI subscription is out of reach. See [economics.md](economics.md). |
| **Open** | Apache-2.0 code, open data, published benchmarks with every error listed, open-weight base models. Anyone can audit it, run it or fork it. | Trust that comes from inspection rather than marketing. No lock-in: it outlives any company, including the one that started it. |
| **Private** | On-device by default. The server binds to localhost and logs nothing. Sync, where wanted, is end-to-end encrypted. See [privacy.md](privacy.md). | Religious belief is sensitive data in law (GDPR art. 9) and in fact: for hundreds of millions of believers it is dangerous data. |
| **Faithful** | One theological boundary, the Creed of 381, enforced transparently, with a proof for every rule-based block. See [theology.md](theology.md). | The minimum shared by Catholic, Orthodox and Protestant churches: firm on God, Christ and the Spirit, fair on what the traditions still debate. |

## One boundary, many profiles

The Creed of 381 is the floor, not the ceiling. Dust ships the Creed as the default
boundary and lets anyone stack more on top:

* **Confession profiles** ([extensions.md](extensions.md)): a church, denomination or
  ministry adds its own confession as a data file (Chalcedon ships as the worked example;
  Westminster, the Catechism, an Orthodox catechism or a local statement of faith would
  follow the same format). The default for everyone else does not change.
* **Forks**: because everything is open, a tradition can fork the whole layer. The
  boundary fingerprint (`dust audit`) makes any change visible, so a deployment can say
  exactly which boundary it enforces. A fork that changes the Creed itself is no longer
  Dust's boundary, and the fingerprint shows it.

## Two ways to use it

1. **Infrastructure for developers.** A Python package and an OpenAI-compatible HTTP API
   that any Bible app, church platform, translation tool or ministry product can put in
   front of any open model. This is the main product: one shared, audited layer instead of
   every ministry building and paying for its own guardrails.
2. **A direct application.** `dust serve` opens **Dust Study** in the browser at
   `http://127.0.0.1:8381`: ask a question, get an answer from the model on your own
   computer, see whether it passed and why. It loads nothing from the internet. It is
   deliberately minimal: a reference app that shows the infrastructure working, which
   others can build better apps on.

## What Dust is not

Not a church, not a pastor and not a spiritual authority. It cannot judge pastoral fit or
replace a community. It checks statements against propositions and says so plainly. See
[uses.md](uses.md).

## Who is behind it

A personal research project led by Daniel Dizon and incubated by Rejoice, building on
research published by Always Foundation ([lineage.md](lineage.md)). It stands on a lot of
other people's work too: [prior-work.md](prior-work.md).
