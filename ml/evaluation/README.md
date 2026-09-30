# ml/evaluation

The actual evaluation pipeline implementation lives in
`backend/app/evaluation/evaluator.py` (it needs direct access to the live
Tool Registry, Policy Engine, and RAG index in the running application, so
it is part of the backend package rather than a standalone script here).

Trigger a run via the API (`POST /api/v1/evaluation/run`), the Evaluation
Dashboard in the frontend, or directly:

    python -c "
    import asyncio
    from app.database.session import AsyncSessionLocal
    from app.evaluation.evaluator import run_evaluation
    asyncio.run(run_evaluation(AsyncSessionLocal(), dataset_name='enterprise_tool_routing_v1', sample_size=300))
    "

This folder is kept for future standalone offline evaluation scripts (e.g.
comparing two fine-tuned checkpoints without the full API running).
