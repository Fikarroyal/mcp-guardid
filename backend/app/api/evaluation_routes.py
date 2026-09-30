from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.evaluation.evaluator import get_evaluation_results, run_evaluation
from app.models.entities import EvaluationRun, User
from app.schemas.misc import EvaluationRunOut, EvaluationRunRequest

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationRunOut)
async def trigger_evaluation(
    payload: EvaluationRunRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> EvaluationRunOut:
    run = await run_evaluation(db, dataset_name=payload.dataset_name, sample_size=payload.sample_size)
    metrics = await get_evaluation_results(db, run.id)
    return EvaluationRunOut(id=run.id, dataset_name=run.dataset_name, model_version=run.model_version,
                             status=run.status, started_at=run.started_at, finished_at=run.finished_at, metrics=metrics)


@router.get("/results", response_model=list[EvaluationRunOut])
async def list_evaluation_results(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[EvaluationRunOut]:
    result = await db.execute(select(EvaluationRun).order_by(EvaluationRun.started_at.desc()).limit(20))
    runs = list(result.scalars().all())
    output = []
    for run in runs:
        metrics = await get_evaluation_results(db, run.id)
        output.append(EvaluationRunOut(id=run.id, dataset_name=run.dataset_name, model_version=run.model_version,
                                        status=run.status, started_at=run.started_at, finished_at=run.finished_at,
                                        metrics=metrics))
    return output


@router.get("/results/{run_id}", response_model=EvaluationRunOut)
async def get_single_evaluation(
    run_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> EvaluationRunOut:
    run = await db.get(EvaluationRun, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation run not found.")
    metrics = await get_evaluation_results(db, run.id)
    return EvaluationRunOut(id=run.id, dataset_name=run.dataset_name, model_version=run.model_version,
                             status=run.status, started_at=run.started_at, finished_at=run.finished_at, metrics=metrics)
