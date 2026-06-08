from app.tools.search import SearchTool, normalize_ddgs_result


def test_normalize_ddgs_result_maps_expected_fields() -> None:
    result = normalize_ddgs_result(
        {
            "title": "Example title",
            "href": "https://example.com/article",
            "body": "Useful summary",
        },
        query="multimodal rag",
    )

    assert result is not None
    assert result.title == "Example title"
    assert result.url == "https://example.com/article"
    assert result.snippet == "Useful summary"
    assert result.query == "multimodal rag"
    assert result.provider == "ddgs"


def test_normalize_ddgs_result_skips_missing_url() -> None:
    result = normalize_ddgs_result({"title": "No URL", "body": "Missing href"}, query="rag")

    assert result is None


def test_search_many_deduplicates_urls() -> None:
    tool = SearchTool(provider="mock", max_results=2)

    results = tool.search_many(["same topic", "same topic again"])

    assert len(results) == 1
    assert results[0]["provider"] == "mock"
    assert results[0]["url"] == "https://example.com/researchflow/mock-source"
