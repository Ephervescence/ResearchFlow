from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import DocumentChunk
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingClient


@dataclass(frozen=True)
class SourceDocument:
    source_id: int | None
    title: str
    url: str
    source_type: str
    content: str


def index_documents(db: Session, task_id: int, documents: list[SourceDocument]) -> int:
    embedding_client = EmbeddingClient()
    chunk_records: list[tuple[SourceDocument, int, str]] = []

    for document in documents:
        chunks = chunk_text(
            document.content,
            max_chars=settings.chunk_max_chars,
            overlap_chars=settings.chunk_overlap_chars,
        )
        for chunk in chunks:
            chunk_records.append((document, chunk.chunk_index, chunk.content))

    if not chunk_records:
        return 0

    embeddings = embedding_client.embed_documents([record[2] for record in chunk_records])
    for (document, chunk_index, content), embedding in zip(chunk_records, embeddings, strict=True):
        db.add(
            DocumentChunk(
                task_id=task_id,
                source_id=document.source_id,
                chunk_index=chunk_index,
                content=content,
                embedding=embedding,
                chunk_metadata={
                    "title": document.title,
                    "url": document.url,
                    "source_type": document.source_type,
                },
            )
        )
    db.commit()
    return len(chunk_records)


def retrieve_relevant_chunks(db: Session, task_id: int, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    embedding = EmbeddingClient().embed_query(query)
    distance = DocumentChunk.embedding.cosine_distance(embedding).label("distance")
    statement = (
        select(DocumentChunk, distance)
        .where(DocumentChunk.task_id == task_id)
        .order_by(distance)
        .limit(top_k or settings.rag_top_k)
    )
    results = []
    for chunk, score in db.execute(statement):
        results.append(
            {
                "id": chunk.id,
                "task_id": chunk.task_id,
                "source_id": chunk.source_id,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
                "metadata": chunk.chunk_metadata,
                "distance": float(score),
            }
        )
    return results
