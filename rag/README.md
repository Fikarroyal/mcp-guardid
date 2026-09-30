# rag/

The RAG pipeline implementation (chunking, embedding, vector search,
retrieval, metadata filtering) lives in `backend/app/rag/` because it needs
direct access to the same database session and vector store used by the
rest of the application. This top-level `rag/` folder mirrors the structure
called for in the project spec and is where standalone ingestion tooling
(e.g. a script to bulk-load new SOP PDFs) would live if/when that's built --
see `scripts/ingest_documents.py` for the current (seed-data-only) entry point.

- `documents/`   -- drop new source documents here for ingestion
- `ingestion/`   -- reserved for standalone ingestion scripts
- `retrieval/`   -- reserved for retrieval experiments/notebooks
- `embeddings/`  -- reserved for exported embedding artifacts
