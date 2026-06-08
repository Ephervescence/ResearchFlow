from typing import TypedDict


class ResearchState(TypedDict, total=False):
    task_id: int
    user_query: str
    plan: dict
    keywords: list[str]
    search_results: list[dict]
    sources: list[dict]
    notes: list[dict]
    recalled_memories: list[dict]
    retrieved_chunks: list[dict]
    reflection: dict
    report_markdown: str
    skipped: bool
    message: str
    errors: list[dict]
