"""
LoRA / QLoRA fine-tuning pipeline (Section 17).

STATUS: this is a complete, runnable pipeline definition, but it is NOT
executed as part of this deliverable -- it requires a GPU runtime and a base
model download, neither of which this sandbox provides. It reads the exact
JSONL datasets produced by `scripts/generate_dataset.py`
(ml/datasets/intent_train.jsonl, tool_selection_train.jsonl,
risk_classification_train.jsonl) and fine-tunes a small causal LM to emit
the same structured JSON the mock/Anthropic LLM providers already produce
(see backend/app/agents/llm_provider.py) -- so a fine-tuned model can be
dropped in as a third `LLMProvider` implementation without changing any
other part of the architecture (Section 45's "adapter" requirement).

Run (on a GPU host, with `pip install torch transformers peft bitsandbytes accelerate`):
    python -m ml.fine_tuning.train_lora --task intent --base-model <hf-model-id>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DATASET_DIR = Path(__file__).resolve().parents[1] / "datasets"

TASK_FILES = {
    "intent": "intent_train.jsonl",
    "tool_selection": "tool_selection_train.jsonl",
    "risk": "risk_classification_train.jsonl",
}

PROMPT_TEMPLATE = """### Instruction:
{instruction}

### Input:
{input}

### Response:
{output}"""


def load_examples(task: str) -> list[dict]:
    path = DATASET_DIR / TASK_FILES[task]
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python -m scripts.generate_dataset` first."
        )
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def format_example(task: str, row: dict) -> str:
    if task == "intent":
        instruction = "Identify the correct enterprise infrastructure intent."
        input_text = row["input"]
        output = json.dumps(row["output"], ensure_ascii=False)
    elif task == "tool_selection":
        instruction = "Select the correct MCP tools for this request, from the retrieved candidates only."
        input_text = row["input"]
        output = json.dumps(row["output"], ensure_ascii=False)
    else:  # risk
        instruction = "Classify the risk level and approval requirement for this request."
        input_text = row["input"]
        output = json.dumps(row["output"], ensure_ascii=False)
    return PROMPT_TEMPLATE.format(instruction=instruction, input=input_text, output=output)


def build_training_pipeline(task: str, base_model: str, output_dir: Path):
    """Constructs (but does not run) the full LoRA fine-tuning pipeline.

    Kept as a function -- rather than executed at import time -- so this
    module can be imported by tests/tooling without requiring torch/peft
    to be installed in every environment."""
    try:
        import torch
        from datasets import Dataset
        from peft import LoraConfig, TaskType, get_peft_model
        from transformers import (
            AutoModelForCausalLM,
            AutoTokenizer,
            DataCollatorForLanguageModeling,
            Trainer,
            TrainingArguments,
        )
    except ImportError as exc:  # pragma: no cover - expected outside a GPU training host
        raise RuntimeError(
            "Fine-tuning dependencies are not installed. On a GPU host run:\n"
            "  pip install torch transformers peft bitsandbytes accelerate datasets"
        ) from exc

    examples = load_examples(task)
    texts = [format_example(task, row) for row in examples]
    dataset = Dataset.from_dict({"text": texts})

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=512, padding="max_length")

    tokenized = dataset.map(tokenize, batched=True, remove_columns=["text"])

    model = AutoModelForCausalLM.from_pretrained(base_model, torch_dtype=torch.bfloat16, device_map="auto")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],  # adjust per base model architecture
    )
    model = get_peft_model(model, lora_config)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=4,
        gradient_accumulation_steps=4,
        num_train_epochs=3,
        learning_rate=2e-4,
        logging_steps=10,
        save_strategy="epoch",
        bf16=True,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    return trainer


def main():
    parser = argparse.ArgumentParser(description="MCP-GuardID LoRA/QLoRA fine-tuning (train/eval kept separate from production)")
    parser.add_argument("--task", choices=list(TASK_FILES), required=True)
    parser.add_argument("--base-model", required=True, help="HF model id, e.g. a small instruction-tuned base model")
    parser.add_argument("--output-dir", default="ml/fine_tuning/checkpoints")
    args = parser.parse_args()

    trainer = build_training_pipeline(args.task, args.base_model, Path(args.output_dir))
    trainer.train()
    trainer.save_model(args.output_dir)
    print(f"Fine-tuned adapter for task='{args.task}' saved to {args.output_dir}")
    print("NOTE: evaluate this checkpoint with `ml/evaluation/` BEFORE wiring it into "
          "app/agents/llm_provider.py as a new LLMProvider -- never point production traffic "
          "at an unevaluated checkpoint.")


if __name__ == "__main__":
    main()
