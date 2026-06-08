from pathlib import Path

import pytest

from app.tools.document_reader import (
    UnsupportedDocumentTypeError,
    detect_file_type,
    parse_local_document,
)


def test_detect_file_type_supports_mvp_formats() -> None:
    assert detect_file_type("paper.pdf") == "pdf"
    assert detect_file_type("notes.md") == "markdown"
    assert detect_file_type("summary.markdown") == "markdown"
    assert detect_file_type("source.txt") == "text"


def test_detect_file_type_rejects_unknown_extension() -> None:
    with pytest.raises(UnsupportedDocumentTypeError):
        detect_file_type("archive.zip")


def test_parse_markdown_document(tmp_path: Path) -> None:
    path = tmp_path / "notes.md"
    path.write_text("# RAG\n\nRetrieval augmented generation note.", encoding="utf-8")

    result = parse_local_document(path, max_chars=200)

    assert "Retrieval augmented generation" in result


def test_parse_pdf_document(tmp_path: Path) -> None:
    import pymupdf

    path = tmp_path / "paper.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "Multimodal RAG PDF note")
    document.save(path)
    document.close()

    result = parse_local_document(path, max_chars=200)

    assert "Multimodal RAG PDF note" in result
