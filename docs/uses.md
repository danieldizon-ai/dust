# Uses: a Scripture study layer, in many languages

Dust is infrastructure. It becomes useful inside tools other people build. These are the
uses it is designed for, and the ones it is not.

## Designed for

* **Bible study and teaching preparation.** A model that explains a passage, outlines a
  study or summarises how different traditions read a text, while staying inside the
  Creed and quoting Scripture from a real translation rather than from memory. The
  retrieval step already puts the relevant article and verses in front of the model; a
  full study tool should add passage retrieval (for example the companion `web-bible-rag`
  dataset, World English Bible, CC0) and reference checking.
* **Church history and doctrine.** Because describing is not asserting, the layer lets a
  model explain Arius, Sabellius or Marcion accurately, and blocks only when the model
  adopts their positions as its own.
* **Comparative questions.** On baptism, the Eucharist, the papacy, Mary, justification
  and the other latitude topics, the constitution asks for a fair account of each tradition
  and the benchmark checks that such statements are not blocked.
* **Translation and seminary work.** Larger tiers can help translators compare renderings
  of creedal and Christological passages, with the Greek anchors in `creed.json` as a
  reference point.
* **A building block.** Bible apps, church software and ministry tools can call the HTTP
  API (`/v1/check`, `/v1/chat/completions`) or the Python package rather than rebuilding
  doctrinal guardrails themselves.

## Not designed for

Following Always Foundation's ADR 0018, which Dust adopts: no AI companion or persona, no
AI pastor or anything presented as spiritual authority, no emotional, mental-health or
crisis support, nothing aimed at children, and no engagement features designed to keep
people talking. The constitution tells the model to hand personal crises to people.

## Multilingual use

The Creed's own history is multilingual (Greek original, Latin, Syriac, Coptic, Armenian
and every later language), and Dust carries the Greek and Latin texts. Model support is
uneven, and the measured state is plain:

| Language | Symbolic track | Neural guard | Measured (block or flag, all eval items) |
|---|---|---|---|
| English | Yes | Trained | recall 0.87, false positives 4.8% (counting flags) |
| Spanish, Portuguese | No | Trained on a small set; may block | 12 of 14 items correct |
| French, German, Tagalog, Indonesian | No | Not trained; may only flag | French 3 of 4 contradictions surfaced; German, Tagalog, Indonesian largely missed |

Three ways to extend coverage, in order of cost:

1. **Pivot translation.** `Layer(translate=...)` translates a non-English draft to English
   before checking. With the wrapped model doing the translation, every language the model
   speaks gets the English checker. Always's research cites evidence that reasoning in
   English and translating the answer narrows the gap for some African languages; the same
   idea applies to checking. The cost is one extra generation and translation errors.
2. **Translate the training set.** Machine-translate `data/train.jsonl` per language and
   retrain the guard; review samples by native speakers.
3. **A multilingual transformer guard**, which is the real fix and needs compute.

Open Scripture text matters as much as the model. Always's Scripture server bundles
public-domain or openly licensed Bibles in English, Spanish, Portuguese, Russian, Chinese,
Tagalog and Vietnamese; many languages with large Christian populations still lack an
openly licensed Bible, and that is a limit on any free tool.
