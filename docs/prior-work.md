# Prior work and credit

Dust is not the first attempt to bring AI and the Christian faith together, and it would
not exist without other people's work. This page gives credit and explains how Dust
relates to each effort. Descriptions are of public information as we understand it;
corrections are welcome.

## Christian AI products and research

* **Always Foundation.** The direct ancestor. Its research on free, private Christian AI
  with the Creed of 381 as the only boundary (ADRs 0015-0018, the Always AI research paper,
  the position paper on Christian AI alignment) supplied the choice of boundary, the first
  propositions, the alignment pathway, the model tiers and the private-sync design. Used
  under CC BY 4.0. See [lineage.md](lineage.md).
* **Magisterium AI** (Longbeard). A Catholic AI that answers from a large corpus of Church
  documents and cites its sources. It showed early and at scale that people want
  faith-specific AI that is grounded and cited. Dust differs in scope (a cross-tradition
  minimum rather than one tradition's full teaching), in form (open infrastructure on the
  user's device rather than a hosted service) and in method (checking outputs against
  propositions as well as retrieving sources). A Catholic deployment of Dust could stack a
  Catechism profile on top; Magisterium AI's citation-first approach is a model for how
  such a profile should behave.
* **Gloo's Flourishing AI benchmark** (2025). Measures how well general models support
  human flourishing across several dimensions, including faith. It pushed the question of
  values-aligned evaluation into the open. Dust's benchmark is narrower (doctrinal
  consistency with one creed) and could sit alongside it.
* **Logos / Faithlife** and other Bible-software makers have added AI-assisted search and
  summaries to large theological libraries. They show the value of AI over trusted texts;
  Dust aims to give smaller apps the same kind of grounding for free.
* **SIL International** (Scripture Forge and machine-assisted drafting) and other Bible
  translation organisations. Their work on low-resource languages is where Dust's
  multilingual roadmap most needs partners.

## Church statements on AI

These shaped the constitution's tone (honesty about limits, human dignity, no claim to
spiritual authority):

* Dicastery for the Doctrine of the Faith and Dicastery for Culture and Education,
  *Antiqua et Nova*: note on the relationship between artificial intelligence and human
  intelligence (January 2025).
* *Rome Call for AI Ethics* (Pontifical Academy for Life and others, 2020).
* Ethics and Religious Liberty Commission, *Artificial Intelligence: An Evangelical
  Statement of Principles* (2019).
* The interfaith network **AI and Faith**, for years of convening technologists and
  theologians.

## Open data Dust builds on

* The **World English Bible** (public domain) and **eBible.org**.
* **STEPBible** data (Tyndale House, Cambridge; CC BY) and **OpenBible.info** cross
  references (CC BY), recommended for larger retrieval indexes.
* Public-domain editions of the Creed in Greek and Latin.

## Open models and AI research

* Open-weight model makers: Alibaba (Qwen), Google (Gemma), Meta (Llama), Mistral AI,
  Microsoft (Phi), DeepSeek, and the fully open projects Ai2 (OLMo) and Hugging Face
  (SmolLM). Dust wraps their models; it does not replace their alignment work.
* **Thinking Machines Lab**: "LoRA Without Regret" (2025), which supports Dust's adapter
  route, the Tinker fine-tuning service, and their work on reproducible inference.
* **Ollama** and **llama.cpp**, which make local models practical on ordinary hardware.
* Methods: constitutional AI (Anthropic), DPO (Rafailov et al.), LoRA and QLoRA, Llama
  Guard (Meta), AlphaGeometry (Google DeepMind). Full references are in
  [methods.md](methods.md).

## How to be credited

If your work should be on this page, or is described inaccurately, open an issue. Credit
here is gratitude, not endorsement: none of the people or organisations listed have
reviewed or endorsed Dust.
