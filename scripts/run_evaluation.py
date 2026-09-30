"""
Run:
    python -m scripts.run_evaluation --sample-size 300 --dataset enterprise_tool_routing_v1

Computes every metric in Section 19 by actually exercising the intent
classifier, tool retrieval engine, policy engine, and injection scanners
against the generated test-split datasets (ml/datasets/*_test.jsonl) --
nothing is hardcoded. Requires the database to already be seeded
(`python -m scripts.seed_database`) and the datasets already generated
(`python -m scripts.generate_dataset`).
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database.session import AsyncSessionLocal  # noqa: E402
from app.evaluation.evaluator import get_evaluation_results, run_evaluation  # noqa: E402


async def main(dataset_name: str, sample_size: int) -> None:
    async with AsyncSessionLocal() as db:
        run = await run_evaluation(db, dataset_name=dataset_name, sample_size=sample_size)
        metrics = await get_evaluation_results(db, run.id)

    print(f"Evaluation run {run.id} ({run.status})")
    print(f"Dataset: {run.dataset_name} | Model: {run.model_version}")
    print("-" * 60)
    for name, value in sorted(metrics.items()):
        if "latency" in name:
            print(f"  {name:42s} {value:8.1f} ms")
        else:
            print(f"  {name:42s} {value * 100:7.2f} %")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="enterprise_tool_routing_v1", dest="dataset_name")
    parser.add_argument("--sample-size", default=200, type=int)
    args = parser.parse_args()
    asyncio.run(main(args.dataset_name, args.sample_size))
