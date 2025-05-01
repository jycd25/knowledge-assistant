"""Runtime configuration. Everything comes from env vars prefixed KA_ or a .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="KA_", env_file=".env", extra="ignore")

    data_dir: Path = Path.home() / ".knowledge-assistant"
    host: str = "127.0.0.1"
    port: int = 8765

    # Embeddings are always local. 384 dims matches bge-small.
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384

    # LLM provider: "ollama" | "openai" | "anthropic" | "none"
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    ollama_host: str = "http://127.0.0.1:11434"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None

    chunk_tokens: int = 512
    chunk_overlap_tokens: int = 64

    @property
    def db_path(self) -> Path:
        return self.data_dir / "knowledge.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    s.uploads_dir.mkdir(parents=True, exist_ok=True)
    return s
