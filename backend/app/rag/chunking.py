"""Chunking stage of the RAG ingestion pipeline (Section 8)."""
import re


def chunk_document(content: str, max_chars: int = 400) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", content.strip())
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > max_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks or [content]
