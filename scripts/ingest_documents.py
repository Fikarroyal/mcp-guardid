"""
Run:
    python -m scripts.ingest_documents

Re-ingests the SOP/document seed content (app/rag/seed_content.py) into the
`documents` / `document_chunks` tables and rebuilds every embedding via
`bootstrap_embeddings`. Safe to re-run at any time -- it is idempotent
(matches by document title) and does not touch tool/user/incident data.

To ingest NEW documents (not just the built-in seed set), drop them as
`{"title", "category", "department", "risk_level", "content"}` dicts into
`SOP_DOCUMENTS` in app/rag/seed_content.py, or extend this script to read
files from rag/documents/.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.bootstrap import bootstrap_embeddings  # noqa: E402
from app.database.session import AsyncSessionLocal  # noqa: E402
from scripts.seed_database import seed_documents  # noqa: E402


async def main() -> None:
    async with AsyncSessionLocal() as db:
        await seed_documents(db)
        await db.commit()
        await bootstrap_embeddings(db)
    print("Document ingestion complete; embeddings rebuilt.")


if __name__ == "__main__":
    asyncio.run(main())
