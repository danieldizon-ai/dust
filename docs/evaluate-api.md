# The evaluation API: Dust as a private checking service

`POST /v1/evaluate` returns Dust's verdict as structured findings that another system can
store, show to a reviewer, or act on: which rule was hit, the evidence, how confident the
checker is, and whether a person should look before anything reaches a seeker. It is
meant for a ministry platform's conversation evaluator, a review step that checks an AI
draft before a responder sees it, or a moderation queue.

It changes nothing about how Dust judges. It is a stable view of `Layer.check`
(`src/dust/findings.py`, schema `dust.findings/0.1`).

## Run it privately

```
export DUST_API_TOKEN="$(openssl rand -hex 24)"
dust serve --host 127.0.0.1 --port 8381 --token-env DUST_API_TOKEN
# or
docker build -t dust . && docker run --rm -p 127.0.0.1:8381:8381 -e DUST_API_TOKEN dust
```

With a token, every route except `/healthz` requires `Authorization: Bearer <token>`.
The token is read from an environment variable, never the command line. Dust loads no
model for this route, makes no outbound calls and logs no request content. Put it on a
private network next to the caller; it is not designed to face the internet.

## Request

Either one text:

```json
{"text": "Jesus is the archangel Michael.", "id": "draft-91", "role": "suggestion"}
```

or the messages of a conversation (at most 200):

```json
{
  "items": [
    {"id": "m1", "role": "seeker",     "text": "Is Jesus an angel?"},
    {"id": "m2", "role": "responder",  "text": "No. The Son is true God from true God."},
    {"id": "m3", "role": "suggestion", "text": "The Holy Spirit is an impersonal force."}
  ],
  "roles": ["responder", "assistant", "suggestion", "agent"],
  "extensions": [],
  "include_notes": true
}
```

* `roles`: which items to evaluate (default shown). A seeker's own words are skipped by
  default: Dust checks what a ministry says, not what a person asks.
* `extensions`: a confession profile stacked on the Creed, for example `chalcedon-451`.
  The response's `boundary.fingerprint` changes with it, so a stored evaluation always
  says which boundary produced it.

## Response

```json
{
  "schema": "dust.findings/0.1",
  "decision": "block",
  "review_required": true,
  "boundary": {"fingerprint": "…64 hex…", "extensions": [], "version": "…"},
  "items": [
    {"id": "m2", "role": "responder", "decision": "pass", "findings": [], "notes": [], "…": "…"},
    {
      "id": "m3", "role": "suggestion", "decision": "block", "review_required": true,
      "language": "en",
      "findings": [{
        "rule_id": "P17",
        "kind": "doctrinal_contradiction",
        "outcome": "block",
        "confidence": 1.0,
        "method": "symbolic",
        "evidence": {"sentence": "The Holy Spirit is an impersonal force.", "proof": ["…"]},
        "explanation": "Contradicts P17: …",
        "excluded_errors": [{"id": "E…", "name": "…", "condemned": "…"}],
        "review": {"required": true, "reasons": ["blocked content should be seen by a person …"]}
      }],
      "notes": []
    }
  ],
  "skipped": [{"id": "m1", "role": "seeker"}]
}
```

### Finding kinds

| kind | rule_id | meaning |
|---|---|---|
| `doctrinal_contradiction` | `P01`–`P24`, extension ids (`C01`…) | asserts something the boundary excludes; symbolic findings carry a proof |
| `creed_silence` | `P…` | says the Creed leaves open a point it decides |
| `latitude_overclaim` | `L01`–`L11` | says the Creed settles a question it leaves open |
| `scripture_reference` | `REF` | a book, chapter or verse that does not exist |
| `scripture_quote` | `QUOTE` | a quotation that does not match the cited verse (when a Bible text is loaded) |
| `obfuscation` | `OBF` | look-alike or invisible characters were removed before checking |

### Notes: denominational differences

A `note` of kind `latitude` means the text takes a side on a question the Creed of 381
leaves open (baptism, the Lord's Supper, church order, the Filioque, and so on). It is a
legitimate difference between Christians, reported so a reviewer can see that Dust
deliberately did not object. It is never an error.

### Review policy

`review.required` is true for every block, every neural-only finding (no proof), every
finding outside the languages the guard was validated in, and every Scripture problem.
Dust never recommends acting on a finding without a person.

## Limits

Use the numbers in [findings.md](findings.md) and [evaluation.md](evaluation.md): on the
held-out benchmark Dust has high precision and moderate recall, so a `pass` means "no
excluded position found", not "theologically sound". Multilingual coverage is the main
gap. Every finding is a prompt for a person, not a verdict on one.
