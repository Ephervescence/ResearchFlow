from app.agent.workflow import limit_search_keywords


def test_limit_search_keywords_deduplicates_and_caps_queries() -> None:
    keywords = limit_search_keywords(
        [
            "multimodal rag",
            " multimodal rag ",
            "multimodal rag papers projects",
            "multimodal rag methods trends",
            "memory text should not be used",
        ]
    )

    assert keywords == [
        "multimodal rag",
        "multimodal rag papers projects",
        "multimodal rag methods trends",
    ]
