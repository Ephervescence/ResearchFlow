from pathlib import Path

from app.tools.reader import truncate_text


SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".md", ".markdown", ".txt"}


class UnsupportedDocumentTypeError(ValueError):
    pass


def detect_file_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".txt":
        return "text"
    raise UnsupportedDocumentTypeError(f"Unsupported file type: {suffix or 'unknown'}")


def parse_local_document(path: Path, max_chars: int) -> str:
    file_type = detect_file_type(path.name)
    if file_type == "pdf":
        return parse_pdf(path, max_chars)
    return parse_text_document(path, max_chars)


def parse_text_document(path: Path, max_chars: int) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    return truncate_text(text, max_chars)


def parse_pdf(path: Path, max_chars: int) -> str:
    import pymupdf

    parts: list[str] = []
    with pymupdf.open(path) as document:
        for page in document:
            parts.append(page.get_text())
            if sum(len(part) for part in parts) >= max_chars:
                break
    return truncate_text("\n".join(parts), max_chars)
