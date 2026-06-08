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
