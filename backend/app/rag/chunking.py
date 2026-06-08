from dataclasses import dataclass


@dataclass(frozen=True)
class TextChunk:
    content: str
    chunk_index: int


def chunk_text(text: str, max_chars: int, overlap_chars: int) -> list[TextChunk]:
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized:
        return []
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be non-negative and smaller than max_chars")

    chunks: list[TextChunk] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        chunks.append(TextChunk(content=normalized[start:end], chunk_index=len(chunks)))
        if end == len(normalized):
            break
        start = end - overlap_chars
    return chunks
