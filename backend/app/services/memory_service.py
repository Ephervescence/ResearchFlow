from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Memory
from app.rag.embeddings import EmbeddingClient
from app.tools.reader import truncate_text


def build_memory_content(user_query: str, notes: list[dict], retrieved_chunks: list[dict]) -> str:
    note_text = "\n".join(str(note.get("content", "")) for note in notes)
    chunk_text = "\n".join(
        f"- {chunk.get('metadata', {}).get('title')}: {truncate_text(str(chunk.get('content', '')), 400)}"
        for chunk in retrieved_chunks[:3]
    )
    content = f"""研究主题：{user_query}

阶段性结论：
{truncate_text(note_text, 1200)}

关键证据：
{truncate_text(chunk_text, 1200)}
"""
    return truncate_text(content, 2400)


def create_memory(
    db: Session,
    content: str,
    *,
    task_id: int | None = None,
    memory_type: str = "long_term_memory",
    tags: list[str] | None = None,
) -> Memory:
    embedding = EmbeddingClient().embed_query(content)
    memory = Memory(
        task_id=task_id,
        content=content,
        embedding=embedding,
        memory_type=memory_type,
        tags=tags or [],
    )
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def search_memories(db: Session, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
    embedding = EmbeddingClient().embed_query(query)
    distance = Memory.embedding.cosine_distance(embedding).label("distance")
    statement = (
        select(Memory, distance)
        .where(Memory.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k or settings.rag_top_k)
    )

    results = []
    for memory, score in db.execute(statement):
        results.append(
            {
                "id": memory.id,
                "task_id": memory.task_id,
                "content": memory.content,
                "memory_type": memory.memory_type,
                "tags": memory.tags,
                "distance": float(score),
                "created_at": memory.created_at,
            }
        )
    return results


def list_memories(db: Session, limit: int = 50) -> list[Memory]:
    statement = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
    return list(db.scalars(statement))
