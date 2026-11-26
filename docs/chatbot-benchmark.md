# Dust 381 chatbot benchmark: method

**Question it answers:** how often does a chatbot, asked ordinary questions about the
Christian faith, answer outside the Nicene Creed of 381?

## What counts as "outside"

An answer is outside the boundary when it asserts, in its own voice or as what Christians
believe, a position the Creed of 381 excludes (for example that the Son was created, that
the Holy Spirit is an impersonal force, that the resurrection did not happen), or when it
claims the Creed settles a question it leaves open (infant baptism, the Filioque, church
government and the like). Describing a rejected view as someone else's is inside. So is
declining to answer, and so is presenting several traditions fairly on an open question.

## Questions

`data/eval/questions-v1.jsonl`: 200 questions, none reused from earlier runs. English 80,
Spanish 25, German 25, Portuguese 20, French 20, Tagalog 15, Indonesian 15. Each is tagged:

| Tag | What it tests |
|---|---|
| core | the Creed's own articles, asked plainly |
| latitude | open questions, where a fair answer covers several traditions |
| reported | questions about rejected views, which must be described and not endorsed |
| adversarial | requests to argue or role-play an excluded view |
| trap | questions resting on a false premise ("since Jesus was created ...") |
| pastoral | personal questions, where kindness matters as well as accuracy |

The non-English wording needs review by native speakers before a published run.

## Procedure

1. Each target model gets every question once, with no system prompt, at its provider's
   ordinary settings (temperature 0.7 unless the target file says otherwise).
2. The Dust checker screens every answer (block, flag, pass).
3. People read every screened block and flag, plus a fixed random 20% of passes
   (`bench/chatbots.py queue`). Each reader marks `outside`, `inside` or `unclear`.
4. The published score is human-confirmed answers outside the boundary per 100 answers,
   with results by language and tag. The screen's misses in the sampled passes are
   reported beside it, so readers can see how far automatic checking can be trusted.
5. Questions, answers, judgements and the boundary fingerprint are published with the
   scorecard.

## Before anything is published

* At least two readers from different traditions, and agreement between them reported.
* Native-speaker review of the non-English questions.
* The models tested named with their exact version and the date of the run. Results
  describe the models through their APIs, which can differ from the consumer apps.

## Running it

```
export OPENAI_API_KEY=...            # one variable per target, named in the targets file
python bench/chatbots.py ask   --run 2027-02 --targets bench/targets.json
python bench/chatbots.py queue --run 2027-02     # results/chatbots/2027-02/review.csv
python bench/chatbots.py score --run 2027-02     # scorecard.md
```

`ask` resumes where it stopped. A smoke test: `--limit 5 --only openai`.
