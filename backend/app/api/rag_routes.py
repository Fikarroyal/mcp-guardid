from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import get_db
from app.models.entities import User
from app.rag.retriever import search_documents
from app.schemas.misc import RagSearchRequest, RagSearchResult

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


@router.post("/search", response_model=list[RagSearchResult])
async def rag_search(
    payload: RagSearchRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db),
) -> list[dict]:
    results = await search_documents(db, query=payload.query, category=payload.category, top_k=payload.top_k)
    return [RagSearchResult(document_id=r["document_id"], title=r["title"], category=r["category"],
                             similarity=r["similarity"], snippet=r["snippet"]) for r in results]
