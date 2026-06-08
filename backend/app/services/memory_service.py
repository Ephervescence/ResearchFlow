import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Memory
from app.rag.embeddings import EmbeddingClient
from app.tools.reader import truncate_text

MEMORY_MAX_RESULTS = 2
MEMORY_MAX_DISTANCE = 0.45
_MEMORY_STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "from",
    "that",
    "this",
    "about",
    "into",
    "over",
    "under",
    "what",
    "how",
}
_ASCII_TERM_RE = re.compile(r"[a-z0-9][a-z0-9_+.-]*")
_CJK_TERM_RE = re.compile(r"[\u4e00-\u9fff]+")


def extract_memory_terms(text: str) -> set[str]:
    normalized = text.lower()
    terms = {
        term
        for term in _ASCII_TERM_RE.findall(normalized)
        if len(term) >= 2 and term not in _MEMORY_STOPWORDS
    }
    for segment in _CJK_TERM_RE.findall(normalized):
        if len(segment) >= 2:
            terms.add(segment)
        if len(segment) >= 3:
            terms.update(segment[index : index + 2] for index in range(len(segment) - 1))
    return terms


def is_short_memory_query(query: str) -> bool:
    compact = "".join(query.split())
    return len(compact) < 6 and len(extract_memory_terms(query)) < 2


def filter_memory_results(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    max_distance: float = MEMORY_MAX_DISTANCE,
    max_results: int = MEMORY_MAX_RESULTS,
) -> list[dict[str, Any]]:
    if is_short_memory_query(query):
        return []

    query_terms = extract_memory_terms(query)
    filtered: list[dict[str, Any]] = []
    for candidate in candidates:
        distance = float(candidate.get("distance", 1.0))
        if distance > max_distance:
            continue
        content_terms = extract_memory_terms(str(candidate.get("content", "")))
        matched_terms = sorted(query_terms & content_terms)
        if query_terms and not matched_terms:
            continue

        enriched = dict(candidate)
        enriched["confidence"] = "high"
        enriched["matched_terms"] = matched_terms[:5]
        filtered.append(enriched)
        if len(filtered) >= max_results:
            break

    return filtered


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
    if is_short_memory_query(query):
        return []

    final_limit = min(top_k or MEMORY_MAX_RESULTS, MEMORY_MAX_RESULTS)
    candidate_limit = max(top_k or settings.rag_top_k, settings.rag_top_k, MEMORY_MAX_RESULTS)
    embedding = EmbeddingClient().embed_query(query)
    distance = Memory.embedding.cosine_distance(embedding).label("distance")
    statement = (
        select(Memory, distance)
        .where(Memory.embedding.is_not(None))
        .order_by(distance)
        .limit(candidate_limit)
    )

    candidates = []
    for memory, score in db.execute(statement):
        candidates.append(
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
    return filter_memory_results(query, candidates, max_results=final_limit)


def list_memories(db: Session, limit: int = 50) -> list[Memory]:
    statement = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
    return list(db.scalars(statement))
