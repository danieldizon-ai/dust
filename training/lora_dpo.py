"""RECIPE, NOT RUN IN THIS REPOSITORY'S CI OR SANDBOX.

LoRA + DPO fine-tuning of a small open model toward the Dust constitution, using
Hugging Face TRL and PEFT. It exists so the method in docs/methods.md is concrete and
reviewable; it has not been executed by the author yet (the sandbox that built v0.1 had
no GPU and no access to Hugging Face). Treat any numbers you get as yours to verify with
bench/run.py and bench/e2e.py.

    pip install "torch>=2.3" "transformers>=4.44" "trl>=0.11" "peft>=0.12" datasets
    python training/dpo_pairs.py > data/dpo_pairs.jsonl
    python training/lora_dpo.py --model Qwen/Qwen2.5-1.5B-Instruct --out adapters/dust-lora-qwen2.5-1.5b

Choose a base model whose licence allows modification and redistribution of adapters
(Apache-2.0 or MIT preferred; see docs/model-family.md). Rough compute: a 1.5B model with
LoRA r=16 on ~50 pairs x 3 epochs fits a single 16-24 GB GPU or Apple silicon with 32 GB,
in minutes; 7-8B needs ~24 GB with 4-bit loading (QLoRA).
"""
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--data", default="data/dpo_pairs.jsonl")
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--beta", type=float, default=0.1)
    args = ap.parse_args()

    from datasets import load_dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from trl import DPOConfig, DPOTrainer

    tok = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype="auto")
    ds = load_dataset("json", data_files=args.data, split="train")
    peft_cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")
    cfg = DPOConfig(output_dir=args.out, num_train_epochs=args.epochs, beta=args.beta, learning_rate=5e-6,
                    per_device_train_batch_size=2, gradient_accumulation_steps=4, logging_steps=5, save_strategy="epoch")
    trainer = DPOTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tok, peft_config=peft_cfg)
    trainer.train()
    trainer.save_model(args.out)
    print(f"adapter saved to {args.out}; evaluate with bench/e2e.py before publishing")


if __name__ == "__main__":
    main()
