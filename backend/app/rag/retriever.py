"""
RAG retrieval pipeline (Section 8):
    Documents -> Chunking -> Embedding -> Vector DB -> Retriever
    -> Relevant Context -> Planner / Verifier
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document, DocumentChunk
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store
from app.security.injection_defense import scan_document


async def search_documents(
    db: AsyncSession, *, query: str, category: str | None = None, top_k: int = 5
) -> list[dict]:
    provider = get_embedding_provider()
    vector_store = get_vector_store()
    query_vector = provider.embed(query)

    metadata_filter = {"category": category} if category else None
    results = vector_store.search(namespace="rag_documents", query_vector=query_vector, top_k=top_k,
                                   metadata_filter=metadata_filter)

    if not results:
        return []

    chunk_ids = [r.id for r in results]
    chunks_result = await db.execute(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids)))
    chunks_by_id = {c.id: c for c in chunks_result.scalars().all()}

    doc_ids = {c.document_id for c in chunks_by_id.values()}
    docs_result = await db.execute(select(Document).where(Document.id.in_(doc_ids)))
    docs_by_id = {d.id: d for d in docs_result.scalars().all()}

    output = []
    for r in results:
        chunk = chunks_by_id.get(r.id)
        if not chunk:
            continue
        doc = docs_by_id.get(chunk.document_id)
        if not doc:
            continue
        findings = scan_document(chunk.content, source_label=f"document:{doc.title}")
        output.append({
            "document_id": doc.id,
            "title": doc.title,
            "category": doc.category,
            "similarity": round(r.score, 4),
            "snippet": chunk.content[:280],
            "security_findings": [f.finding_type for f in findings],
        })
    return output
