"""
Run:
    python -m scripts.generate_dataset
Writes JSONL train/validation/test splits into ml/datasets/.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.evaluation.dataset_generator import generate_all  # noqa: E402

if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parents[1] / "ml" / "datasets"
    summary = generate_all(output_dir)
    print(f"Datasets written to {output_dir}")
    for name, counts in summary.items():
        print(f"  {name:22s} total={counts['total']:<6d} train={counts['train']:<6d} "
              f"val={counts['validation']:<6d} test={counts['test']:<6d}")
