from app.services.citation_service import build_citation_items, format_citation_references


def test_build_citation_items_numbers_and_deduplicates() -> None:
    chunks = [
        {
            "id": 10,
            "source_id": 1,
            "content": "First evidence chunk.",
            "metadata": {"title": "Paper A", "url": "https://example.com/a"},
        },
        {
            "id": 10,
            "source_id": 1,
            "content": "Duplicate evidence chunk.",
            "metadata": {"title": "Paper A", "url": "https://example.com/a"},
        },
        {
            "id": 11,
            "source_id": 2,
            "content": "Second evidence chunk.",
            "metadata": {"title": "Paper B", "url": "https://example.com/b"},
        },
    ]

    items = build_citation_items(chunks)

    assert len(items) == 2
    assert [item["citation_index"] for item in items] == [1, 2]
    assert items[0]["title"] == "Paper A"
    assert items[1]["title"] == "Paper B"


def test_format_citation_references_outputs_numbered_sources() -> None:
    references = format_citation_references(
        [
            {
                "citation_index": 1,
                "title": "Paper A",
                "url": "https://example.com/a",
                "quote": "Important evidence.",
            }
        ]
    )

    assert "[1] Paper A - https://example.com/a" in references
    assert "> Important evidence." in references


def test_format_citation_references_handles_empty_list() -> None:
    assert "暂无可追踪引用" in format_citation_references([])
