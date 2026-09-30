# ml/training

See `ml/fine_tuning/train_lora.py` for the LoRA/QLoRA training pipeline.
This folder is reserved for training run artifacts (logs, checkpoints,
tokenizer configs) produced by that script -- kept separate from
`ml/fine_tuning/` so checkpoints can be gitignored independently of the
pipeline code itself.
