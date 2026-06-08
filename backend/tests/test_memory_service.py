from app.services.memory_service import build_memory_content


def test_build_memory_content_includes_query_notes_and_chunks() -> None:
    content = build_memory_content(
        "multimodal rag",
        [{"content": "RAG combines retrieval and generation."}],
        [
            {
                "content": "Vision-language retrieval can ground answers in images.",
                "metadata": {"title": "VL Retrieval"},
            }
        ],
    )

    assert "multimodal rag" in content
    assert "RAG combines retrieval" in content
    assert "VL Retrieval" in content
    assert "Vision-language retrieval" in content


def test_build_memory_content_is_bounded() -> None:
    content = build_memory_content(
        "x" * 1000,
        [{"content": "n" * 5000}],
        [{"content": "c" * 5000, "metadata": {"title": "Long"}}],
    )

    assert len(content) <= 2403
