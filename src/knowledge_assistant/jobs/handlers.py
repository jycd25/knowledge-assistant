"""Job handlers. Each takes (job, progress) and returns a result dict. Registered in the container."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from ..core.embeddings import Embedder
from ..core.models import Job
from ..core.repositories import EntryRepository
from .pdf_extract import extract_in_subprocess
from .worker import ProgressFn


class Handlers:
    def __init__(self, session_factory: sessionmaker[Session], embedder: Embedder, chunk_tokens: int, overlap_tokens: int,
                 pdf_engine: str = "pymupdf"):
        self.sf = session_factory
        self.embedder = embedder
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens
        self.pdf_engine = pdf_engine

    def _entries(self, s: Session) -> EntryRepository:
        return EntryRepository(s, self.embedder, self.chunk_tokens, self.overlap_tokens)

    def ingest_text(self, job: Job, progress: ProgressFn) -> dict:
        p = job.payload
        progress(10, "chunking and embedding")
        with self.sf() as s, s.begin():
            e = self._entries(s).create(title=p["title"], content=p["content"], topic_id=p.get("topic_id"),
                                        source=p.get("source", "manual"), tags=p.get("tags") or [])
            n = len(e.chunks)
            return {"entry_id": e.id, "chunks": n}

    def ingest_pdf(self, job: Job, progress: ProgressFn) -> dict:
        p = job.payload
        pdf = Path(p["path"])
        progress(5, "extracting text")
        markdown = extract_in_subprocess(pdf, p.get("engine", self.pdf_engine))
        if not markdown.strip():
            raise ValueError("PDF contained no extractable text (scanned image?)")
        progress(50, "chunking and embedding")
        with self.sf() as s, s.begin():
            e = self._entries(s).create(title=p.get("title") or pdf.stem, content=markdown, topic_id=p.get("topic_id"),
                                        source="pdf", tags=p.get("tags") or [])
            n = len(e.chunks)
        if p.get("delete_after", True):
            pdf.unlink(missing_ok=True)
        return {"entry_id": e.id, "chunks": n, "characters": len(markdown)}

    def reindex_entry(self, job: Job, progress: ProgressFn) -> dict:
        with self.sf() as s, s.begin():
            n = self._entries(s).reindex(job.payload["entry_id"])
        return {"chunks": n}
