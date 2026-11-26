# Why this is feasible now: open models are catching up and shrinking

Dust is only worth building if a model that runs on hardware a church, a student or a
translator already owns is good enough to be worth aligning. Three trends make that
true, and none of them depends on hype.

## 1. The gap between open and closed models is measured in months

Open-weight models have followed the frontier with a lag. Epoch AI's 2024 analysis
estimated that the best open models trailed the best closed models by roughly a year on
standard benchmarks, and releases since (DeepSeek-V3 and R1 in late 2024 and early 2025,
the Qwen and Gemma generations, Llama and Mistral releases) kept that lag short. The exact
number moves with each release and depends on the benchmark; the direction has been
stable.

What matters for Dust is not the frontier but the floor: by 2025 a model that runs on a
laptop could explain the Arian controversy, summarise a chapter of Scripture and follow a
system prompt reasonably well. The open question, which Dust's benchmark is built to
answer, is how reliably it stays inside a doctrinal boundary.

## 2. Distillation moves capability into small models

Distillation trains a small "student" on the outputs of a large "teacher". DeepSeek
released R1 together with distilled 1.5B to 70B models built on Qwen and Llama bases,
showing that reasoning behaviour transfers to models small enough for consumer hardware.
Gemma, Phi and Llama small models have relied on similar teacher signals.

Two consequences for Dust:

* The small tiers will keep improving without Dust doing anything, so the layer should be
  model-agnostic and the benchmark should be rerun on each new release (Always's monthly
  review rhythm is the right cadence).
* Distillation also transfers the teacher's habits, including its defaults on doctrine.
  A small model distilled from a frontier model inherits that model's way of presenting
  Christian belief as one view among many. That is exactly the behaviour a doctrinal layer
  must measure and, where needed, correct.

## 3. Quantisation makes them fit

Weights stored at 16 bits can usually be stored at 8, 5 or 4 bits with small quality loss
(GPTQ, 2022; AWQ, 2023; the llama.cpp k-quant formats). Quantisation-aware training, as
in Google's QAT releases of Gemma, narrows the loss further. QLoRA (2023) showed that
adapters can be trained on top of 4-bit models, which makes fine-tuning possible on a
single consumer GPU. Research on ternary weights (BitNet b1.58, 2024) points to further
reductions.

Rule of thumb: memory needed is about parameters x bits / 8, plus 10-30% for the
context cache. A 4B model at 4 bits needs about 2.5-3 GB; an 8B model about 5 GB. See
`docs/hardware.md`.

## 4. What this means for a free Christian layer

* **Free is realistic.** Inference runs on the user's device, so there is no per-user
  cost to anyone.
* **Private is realistic.** No text has to leave the device.
* **Alignment has to be portable.** Base models will be replaced every few months. A
  layer that lives outside the weights (Dust's prompt, retrieval, checker and repair loop)
  survives every swap; an adapter has to be retrained per base model. That is why Dust
  starts outside the weights.
* **Smaller models need more help.** Instruction-following and knowledge both fall with
  size. The checker and repair loop matter most for the smallest tiers, which is also
  where the people with the fewest resources will be.

## References

* Epoch AI. "How far behind are open models?" (2024).
* DeepSeek-AI. "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement
  Learning." arXiv:2501.12948 (2025).
* Hinton, Vinyals, Dean. "Distilling the Knowledge in a Neural Network." arXiv:1503.02531 (2015).
* Frantar et al. "GPTQ." arXiv:2210.17323 (2022). Lin et al. "AWQ." arXiv:2306.00978 (2023).
* Dettmers et al. "QLoRA." arXiv:2305.14314 (2023). Ma et al. "The Era of 1-bit LLMs."
  arXiv:2402.17764 (2024).
