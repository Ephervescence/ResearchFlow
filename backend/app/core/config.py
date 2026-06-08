from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = Field(
        default="postgresql+psycopg://researchflow:researchflow@localhost:5432/researchflow"
    )
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    llm_provider: str = Field(default="mock")
    llm_api_key: str | None = Field(default=None)
    llm_base_url: str | None = Field(default=None)
    llm_model: str = Field(default="deepseek-chat")

    search_provider: str = Field(default="mock")
    search_max_results: int = Field(default=5)
    search_region: str = Field(default="wt-wt")
    search_timeout_seconds: int = Field(default=10)

    reader_timeout_seconds: int = Field(default=15)
    reader_max_chars: int = Field(default=6000)

    upload_dir: Path = Field(default=Path("../data/uploads"))
    upload_max_bytes: int = Field(default=20 * 1024 * 1024)

    embedding_provider: str = Field(default="mock")
    embedding_model: str = Field(default="mock-embedding-384")
    embedding_api_key: str | None = Field(default=None)
    embedding_base_url: str | None = Field(default=None)
    embedding_dimensions: int = Field(default=384)

    chunk_max_chars: int = Field(default=900)
    chunk_overlap_chars: int = Field(default=120)
    rag_top_k: int = Field(default=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
