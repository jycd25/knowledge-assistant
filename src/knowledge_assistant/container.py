"""Composition root: builds every long-lived object once and hands them to the CLI (and the API later)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .core.db import init_schema, make_engine, make_session_factory
from .core.embeddings import Embedder, FastEmbedEmbedder
from .core.llm import LLMProvider, make_provider

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    embedder: Embedder
    llm: LLMProvider

    @classmethod
    def build(cls, settings: Settings, embedder: Embedder | None = None, llm: LLMProvider | None = None) -> "Container":
        engine = make_engine(settings.db_path)
        init_schema(engine, settings.embedding_dim)
        sf = make_session_factory(engine)
        if embedder is None:
            log.info("loading embedding model %s", settings.embedding_model)
            embedder = FastEmbedEmbedder(settings.embedding_model, settings.embedding_dim,
                                         cache_dir=str(settings.data_dir / "models"))
        llm = llm or make_provider(settings)
        return cls(settings, engine, sf, embedder, llm)

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass
