# Hardware requirements

Two parts of Dust have very different costs: the **layer** (checker, guard, retrieval)
and the **base model** it wraps.

## The layer

| Component | Size | Cost per sentence (measured in the sandbox CPU) |
|---|---|---|
| Symbolic checker | ~40 KB of Python, 0 dependencies beyond the standard library | median 0.25 ms |
| Neural guard | 197 KB int8 weights; numpy | median 0.32 ms |
| Dual track | both | median 0.45 ms, p95 1.1 ms |
| Retrieval over the Creed | in memory | microseconds |

Measured by `bench/run.py` on a 4-core cloud VM. Anything that runs Python and numpy runs
the layer, including a Raspberry Pi; checking is a rounding error next to generation.

## The base model

Memory needed is roughly parameters x bits per weight / 8, plus the context (KV) cache.
Figures below are approximate for GGUF-style 4-bit (Q4_K_M) and 8-bit (Q8_0) files with a
few thousand tokens of context.

| Model size | 4-bit file | 8-bit file | Minimum comfortable memory (4-bit) | Typical devices |
|---|---|---|---|---|
| 1-2B | 0.7-1.3 GB | 1.3-2.5 GB | 4 GB phone / 4 GB RAM | Recent phones, browsers with WebGPU, Raspberry Pi 5 |
| 3-4B | 2-2.7 GB | 3.5-4.5 GB | 8 GB | Most laptops from the last five years |
| 7-9B | 4.5-5.5 GB | 8-9.5 GB | 12-16 GB | 16 GB laptops, Apple silicon, 8 GB GPUs |
| 12-14B | 7-9 GB | 13-15 GB | 16-24 GB | Apple silicon 24 GB+, 12-16 GB GPUs |
| 24-32B | 14-20 GB | 26-35 GB | 32-48 GB | 24 GB GPUs, 32-64 GB Macs |
| 70B | ~40 GB | ~75 GB | 64-96 GB | Workstations, 2x 24-48 GB GPUs, 96 GB+ Macs |

Speed varies widely with memory bandwidth. As orders of magnitude, a 4B model at 4 bits
gives tens of tokens per second on Apple silicon or a mid-range GPU and single digits to
low tens on a laptop CPU; phones are slower and thermally limited. Measure on the target
device rather than trusting a table.

## Training (when adapters are trained)

| Job | Hardware |
|---|---|
| LoRA / DPO on 1-2B | One 16 GB GPU, or Apple silicon with 32 GB (MLX), minutes to an hour for a seed set |
| QLoRA on 7-8B | One 24 GB GPU |
| LoRA on 24-32B | 48-80 GB GPU |
| Training a transformer guard (small encoder) | Any modern GPU; a CPU is feasible for a few thousand examples |
| Evaluating a model with `bench/e2e.py` | Whatever runs the model; one run is ~25 questions x 2-4 generations |

The sandbox that built v0.1 had 4 CPU cores, 16 GB of RAM, no GPU and no access to model
downloads, so no base model was run and no adapter was trained. Everything that needs
more than that is marked as such in the repository.
