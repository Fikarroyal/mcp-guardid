"""
Runs once at application startup (see app/main.py lifespan). Fits the
embedding provider on the full live corpus (tool descriptions + document
chunks + intent examples) and populates the vector store namespaces used by
the Tool Retrieval Engine and the RAG Retriever.

Re-running this after `mcp_tools` or `documents` change (e.g. via the seed
script or an admin edit) keeps embeddings in sync -- it is idempotent.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intent import all_example_utterances, build_intent_centroids
from app.models.entities import Document, DocumentChunk, McpTool
from app.rag.embeddings import get_embedding_provider
from app.rag.vector_store import get_vector_store


async def bootstrap_embeddings(db: AsyncSession) -> None:
    provider = get_embedding_provider()
    vector_store = get_vector_store()

    tools_result = await db.execute(select(McpTool))
    tools = list(tools_result.scalars().all())

    chunks_result = await db.execute(select(DocumentChunk))
    chunks = list(chunks_result.scalars().all())

    docs_result = await db.execute(select(Document))
    docs_by_id = {d.id: d for d in docs_result.scalars().all()}

    corpus = [t.description for t in tools] + [c.content for c in chunks] + all_example_utterances()
    if not corpus:
        return
    provider.fit(corpus)

    for tool in tools:
        vec = provider.embed(tool.description)
        tool.semantic_embedding = vec
        vector_store.upsert(
            namespace="mcp_tools", item_id=tool.name, vector=vec,
            metadata={"name": tool.name, "enabled": tool.enabled, "category": tool.category,
                      "risk_level": tool.risk_level},
        )

    for chunk in chunks:
        vec = provider.embed(chunk.content)
        chunk.embedding = vec
        doc = docs_by_id.get(chunk.document_id)
        vector_store.upsert(
            namespace="rag_documents", item_id=chunk.id, vector=vec,
            metadata={"category": doc.category if doc else "", "document_id": chunk.document_id},
        )

    await db.flush()
    await db.commit()

    build_intent_centroids()
