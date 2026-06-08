import math

import pytest

from app.db.models import EMBEDDING_DIM
from app.rag.chunking import chunk_text
from app.rag.embeddings import EmbeddingClient, mock_embedding


def test_chunk_text_splits_with_overlap() -> None:
    chunks = chunk_text("abcdefghij", max_chars=4, overlap_chars=1)

    assert [chunk.content for chunk in chunks] == ["abcd", "defg", "ghij"]
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]


def test_chunk_text_rejects_invalid_overlap() -> None:
    with pytest.raises(ValueError):
        chunk_text("abc", max_chars=5, overlap_chars=5)


def test_mock_embedding_is_stable_and_normalized() -> None:
    first = mock_embedding("multimodal rag retrieval", EMBEDDING_DIM)
    second = mock_embedding("multimodal rag retrieval", EMBEDDING_DIM)

    assert first == second
    assert len(first) == EMBEDDING_DIM
    norm = math.sqrt(sum(value * value for value in first))
    assert norm == pytest.approx(1.0)


def test_embedding_client_falls_back_to_mock_when_provider_fails() -> None:
    class BrokenEmbeddings:
        def create(self, **kwargs):
            raise RuntimeError("embedding endpoint unavailable")

    class BrokenClient:
        embeddings = BrokenEmbeddings()

    client = EmbeddingClient()
    client.provider = "api"
    client.client = BrokenClient()

    embeddings = client.embed_documents(["multimodal rag retrieval"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == EMBEDDING_DIM
