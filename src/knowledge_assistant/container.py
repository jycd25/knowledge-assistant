"""Composition root: builds every long-lived object once and hands them to the API and CLI."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from .config import Settings
from .core.db import init_schema, make_engine, make_session_factory
from .core.embeddings import Embedder, FastEmbedEmbedder
from .core.llm import LLMProvider, make_provider
from .jobs import JobQueue, Worker
from .jobs.handlers import Handlers

log = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    embedder: Embedder
    llm: LLMProvider
    queue: JobQueue
    worker: Worker

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
        queue = JobQueue(sf, max_attempts=settings.job_max_attempts)
        worker = Worker(queue, threads=settings.worker_threads)
        mailbox_factory = None
        if settings.email_configured:
            from .core.email_source import ImapMailbox

            mailbox_factory = lambda: ImapMailbox(settings.imap_host, settings.imap_user, settings.imap_password, settings.imap_port)  # noqa: E731
        h = Handlers(sf, embedder, settings.chunk_tokens, settings.chunk_overlap_tokens, mailbox_factory=mailbox_factory)
        worker.register("ingest_text", h.ingest_text)
        worker.register("ingest_pdf", h.ingest_pdf)
        worker.register("reindex_entry", h.reindex_entry)
        worker.register("sync_email", h.sync_email)
        return cls(settings, engine, sf, embedder, llm, queue, worker)

    def start(self) -> None:
        self.worker.start()

    def stop(self) -> None:
        self.worker.stop()
