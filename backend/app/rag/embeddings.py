import hashlib
import logging
import math

from openai import OpenAI

from app.core.config import settings
from app.db.models import EMBEDDING_DIM

logger = logging.getLogger(__name__)


class EmbeddingClient:
    def __init__(self) -> None:
        self.provider = settings.embedding_provider
        self.model = settings.embedding_model
        self.dimensions = settings.embedding_dimensions
        self.client: OpenAI | None = None

        api_key = settings.embedding_api_key or settings.llm_api_key
        base_url = settings.embedding_base_url or settings.llm_base_url
        if api_key and base_url:
            self.client = OpenAI(api_key=api_key, base_url=base_url)

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if self.provider == "mock" or self.client is None:
            return [mock_embedding(text, EMBEDDING_DIM) for text in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=texts,
                dimensions=self.dimensions,
            )
        except Exception as exc:
            logger.warning("embedding request failed; falling back to mock embeddings: %s", exc)
            return [mock_embedding(text, EMBEDDING_DIM) for text in texts]

        embeddings = [item.embedding for item in response.data]
        for embedding in embeddings:
            if len(embedding) != EMBEDDING_DIM:
                logger.warning(
                    "embedding dimension %s does not match database dimension %s; "
                    "falling back to mock embeddings",
                    len(embedding),
                    EMBEDDING_DIM,
                )
                return [mock_embedding(text, EMBEDDING_DIM) for text in texts]
        return embeddings


def mock_embedding(text: str, dimensions: int) -> list[float]:
    values = [0.0] * dimensions
    tokens = text.lower().split()
    if not tokens:
        tokens = [text.lower()]

    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        for offset, byte in enumerate(digest):
            index = (byte + offset * 31) % dimensions
            values[index] += 1.0 if byte % 2 == 0 else -1.0

    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]
