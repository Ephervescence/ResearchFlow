from http.client import IncompleteRead

from app.tools.reader import ReaderTool, extract_text_from_html, truncate_text


def test_truncate_text_normalizes_whitespace() -> None:
    result = truncate_text("alpha\n\n beta\tgamma", max_chars=100)

    assert result == "alpha beta gamma"


def test_truncate_text_limits_length() -> None:
    result = truncate_text("a" * 20, max_chars=10)

    assert result == "aaaaaaaaaa..."


def test_extract_text_from_html_reads_main_content() -> None:
    html = """
    <html>
      <body>
        <nav>Home About</nav>
        <article>
          <h1>Multimodal RAG</h1>
          <p>Multimodal RAG combines retrieval with vision-language generation.</p>
          <p>It is useful for question answering over images, charts, and text.</p>
        </article>
      </body>
    </html>
    """

    result = extract_text_from_html(html, url="https://example.com", max_chars=500)

    assert "Multimodal RAG" in result
    assert "vision-language generation" in result


def test_reader_uses_snippet_for_mock_result() -> None:
    tool = ReaderTool(max_chars=100)

    result = tool.read(
        {
            "title": "Mock source",
            "url": "https://example.com/mock",
            "snippet": "Snippet text",
            "provider": "mock",
        }
    )

    assert result.readable is False
    assert result.content == "Snippet text"
    assert result.error is None


def test_reader_falls_back_when_download_is_incomplete(monkeypatch) -> None:
    tool = ReaderTool(max_chars=100)

    def raise_incomplete_read(url: str) -> str:
        raise IncompleteRead(b"partial html", 12)

    monkeypatch.setattr(tool, "_download_html", raise_incomplete_read)

    result = tool.read(
        {
            "title": "Interrupted source",
            "url": "https://example.com/article",
            "snippet": "Useful snippet",
            "provider": "ddgs",
        }
    )

    assert result.readable is False
    assert result.content == "Useful snippet"
    assert "IncompleteRead" in str(result.error)


def test_read_many_keeps_going_when_one_source_crashes(monkeypatch) -> None:
    tool = ReaderTool(max_chars=100)

    def read_with_one_failure(search_result: dict[str, str]):
        if search_result["title"] == "Broken":
            raise RuntimeError("reader crashed")
        return tool._fallback_document(
            search_result["title"],
            search_result["url"],
            search_result["snippet"],
            None,
        )

    monkeypatch.setattr(tool, "read", read_with_one_failure)

    results = tool.read_many(
        [
            {"title": "Broken", "url": "https://example.com/broken", "snippet": "Broken snippet"},
            {"title": "Good", "url": "https://example.com/good", "snippet": "Good snippet"},
        ]
    )

    assert len(results) == 2
    assert results[0]["error"] == "reader crashed"
    assert results[1]["title"] == "Good"
