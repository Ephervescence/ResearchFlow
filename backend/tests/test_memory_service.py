from app.services.memory_service import build_memory_content, filter_memory_results, search_memories


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


def test_filter_memory_results_skips_short_queries() -> None:
    results = filter_memory_results(
        "hello",
        [
            {
                "id": 1,
                "content": "multimodal rag retrieval methods",
                "distance": 0.1,
            }
        ],
    )

    assert results == []


def test_filter_memory_results_requires_distance_and_keyword_overlap() -> None:
    results = filter_memory_results(
        "multimodal rag methods",
        [
            {"id": 1, "content": "unrelated robotics memory", "distance": 0.1},
            {"id": 2, "content": "multimodal rag retrieval methods", "distance": 0.46},
            {"id": 3, "content": "multimodal rag retrieval methods", "distance": 0.2},
            {"id": 4, "content": "another multimodal rag project", "distance": 0.3},
            {"id": 5, "content": "extra multimodal rag memory", "distance": 0.25},
        ],
    )

    assert [result["id"] for result in results] == [3, 4]
    assert all(result["confidence"] == "high" for result in results)


def test_search_memories_skips_embedding_for_short_queries(monkeypatch) -> None:
    class ExplodingEmbeddingClient:
        def embed_query(self, query: str):
            raise AssertionError("short queries should not be embedded")

    monkeypatch.setattr("app.services.memory_service.EmbeddingClient", ExplodingEmbeddingClient)

    assert search_memories(db=None, query="test") == []
