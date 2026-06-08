from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ReportCitation
from app.tools.reader import truncate_text


def build_citation_items(retrieved_chunks: list[dict[str, Any]], max_items: int = 6) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[tuple[int | None, int | None, str]] = set()

    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata", {})
        source_id = chunk.get("source_id")
        chunk_id = chunk.get("id")
        url = str(metadata.get("url") or "")
        key = (source_id, chunk_id, url)
        if key in seen:
            continue
        seen.add(key)
        items.append(
            {
                "citation_index": len(items) + 1,
                "source_id": source_id,
                "chunk_id": chunk_id,
                "title": str(metadata.get("title") or "Untitled source"),
                "url": url,
                "quote": truncate_text(str(chunk.get("content") or ""), 500),
            }
        )
        if len(items) >= max_items:
            break
    return items


def save_report_citations(
    db: Session,
    *,
    task_id: int,
    report_id: int,
    citation_items: list[dict[str, Any]],
) -> list[ReportCitation]:
    citations = []
    for item in citation_items:
        citation = ReportCitation(
            task_id=task_id,
            report_id=report_id,
            source_id=item.get("source_id"),
            chunk_id=item.get("chunk_id"),
            citation_index=item["citation_index"],
            title=item["title"],
            url=item["url"],
            quote=item["quote"],
        )
        db.add(citation)
        citations.append(citation)
    db.commit()
    for citation in citations:
        db.refresh(citation)
    return citations


def list_report_citations(db: Session, task_id: int) -> list[ReportCitation]:
    statement = (
        select(ReportCitation)
        .where(ReportCitation.task_id == task_id)
        .order_by(ReportCitation.citation_index)
    )
    return list(db.scalars(statement))


def format_citation_references(citation_items: list[dict[str, Any]]) -> str:
    if not citation_items:
        return "- 暂无可追踪引用。"
    return "\n".join(
        f"[{item['citation_index']}] {item['title']} - {item['url']}\n"
        f"> {item['quote']}"
        for item in citation_items
    )
