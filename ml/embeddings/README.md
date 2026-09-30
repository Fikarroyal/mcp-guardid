# ml/embeddings

The embedding provider implementation lives in `backend/app/rag/embeddings.py`.
This folder is a placeholder for exported/cached embedding artifacts (e.g. a
fitted TF-IDF+SVD pickle, or downloaded weights for a production embedding
model) -- none are checked in here since they are regenerated at startup by
`backend/app/core/bootstrap.py`.
