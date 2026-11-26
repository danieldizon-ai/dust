# Economics: why free, open and private matter

This is a back-of-the-envelope analysis, not a forecast. Every number is an assumption
stated so that it can be argued with.

## Who the global Church is

* About **2.3 billion Christians** (Pew Research Center, 2020 data published 2025), and
  the largest share now lives in sub-Saharan Africa. The centre of gravity of the Church is
  in the Global South.
* Nearly half of the world's people live on less than about $7 a day (World Bank poverty
  estimates). A $20-a-month AI subscription, the common consumer price for frontier
  assistants, is more than a week's income for hundreds of millions of believers.
* Open Doors estimates that more than **360 million Christians** face high levels of
  persecution or discrimination (World Watch List, 2024-25).
* Only about **one in ten** of the world's 7,000+ languages has a full Bible (Wycliffe
  Global Alliance, 2024).

A tool designed for a Western subscriber misses most of the Church on price, language and
safety at once.

## The cost of serving one more person

Assume an active study user asks 30 questions a month. Each request carries the
constitution, the Creed and retrieved articles (~1,000 tokens) and gets ~500 tokens back;
with occasional repairs, call it ~50,000 tokens a month.

| Model | Price assumption (per million tokens) | Per user per month | 10 million users per year |
|---|---|---|---|
| Hosted frontier model | $3-15 | $0.15-0.75 | $18-90 million |
| Hosted small open model | $0.10-0.50 | $0.005-0.025 | $0.6-3 million |
| **On the user's own device** | $0 to the provider | **$0** | **$0** (plus the one-off cost of building and maintaining the software) |

Two things follow. First, small open models are already one to two orders of magnitude
cheaper to host than frontier models, which is why a ministry can afford them at all.
Second, on-device inference removes the marginal cost entirely: the project's cost no
longer grows with the number of users, so it can be free for everyone without ads, data
sales or subscriptions. The user's cost is electricity and a device most already have
(the majority of the world's people now use mobile internet, GSMA 2024).

## Why open

* **A public good is cheaper shared.** If ten denominations or ministries each build their
  own doctrinal guardrails, they pay ten times for overlapping work, and each gets less
  testing. One open layer, with profiles for what differs, costs once and is tested by
  everyone.
* **No lock-in.** Hosted AI prices, terms and content policies change at the vendor's
  discretion; services are withdrawn or geo-blocked. Open code and open weights cannot be
  taken back.
* **Trust is earned by inspection.** Churches can read the boundary, run the benchmark and
  see every error. That is worth more than any claim in a brochure, and it is free to
  verify.
* **It outlives its sponsors.** Open work survives organisational change: if any company
  behind it stops, the boundary, the library and the benchmark stay usable by everyone.

## Why private

* **Religious belief is special-category data** under the GDPR (article 9) and similar
  laws. Holding it creates legal duties and liability for whoever stores it. A tool that
  stores nothing has nothing to breach.
* **For persecuted believers, logs are a risk to life.** A hosted service that records
  questions about baptism or conversion can be subpoenaed, hacked or simply watched on the
  network. On-device inference and no logging remove that risk rather than mitigating it.
* **Pastoral conversations need confidence.** People ask an AI things they would not ask
  in public. Privacy is a precondition for honesty.

## Why sovereign

Sovereignty here means a church or a person controls the tool they depend on: they can
run it offline, choose the model, read the rules and change what they are allowed to
change. It protects against price shocks, policy changes, outages, censorship and
sanctions, which in practice fall hardest on the poorest and most persecuted Christians.

## What Dust itself costs

Order-of-magnitude estimates for the roadmap ([roadmap.md](roadmap.md)):

| Phase | Main cost | Compute |
|---|---|---|
| 1. Evidence | Reviewers' and annotators' time | One computer that can run small models |
| 2. Better checking | An engineer or research student for some months | One GPU for hours to days (hundreds of dollars rented) |
| 3. Training | Reviewed preference data (people) | A few GPU-hours per adapter; days of rented inference for distillation (low thousands of dollars) |
| 4. Infrastructure | Engineering, a security review of private sync | Negligible |

The expensive part is people, not compute: theological review, evaluation written by
others, multilingual review. That is where sponsorship (Rejoice's incubation, and partners
from the traditions) does the most good.

## Sources

Pew Research Center, *How the Global Religious Landscape Changed From 2010 to 2020* (2025);
World Bank poverty and inequality data; Open Doors, *World Watch List*; Wycliffe Global
Alliance, *Scripture access statistics* (2024); GSMA, *The State of Mobile Internet
Connectivity* (2024). Model prices are typical public list prices in 2025 and change often.
