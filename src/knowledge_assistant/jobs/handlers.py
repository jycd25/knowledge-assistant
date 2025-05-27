"""Job handlers. Each takes (job, progress) and returns a result dict. Registered in the container."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session, sessionmaker

from ..core.embeddings import Embedder
from ..core.models import Job
from ..core.email_source import Mailbox, parse_email
from ..core.repositories import EntryRepository, SettingRepository
from .pdf_extract import extract_in_subprocess
from .worker import ProgressFn


class Handlers:
    def __init__(self, session_factory: sessionmaker[Session], embedder: Embedder, chunk_tokens: int, overlap_tokens: int,
                 pdf_engine: str = "pymupdf", mailbox_factory: Callable[[], Mailbox] | None = None):
        self.sf = session_factory
        self.mailbox_factory = mailbox_factory
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

    # -- email ----------------------------------------------------------------------
    def sync_email(self, job: Job, progress: ProgressFn) -> dict:
        """Pull new messages since the last synced UID and file each as an entry."""
        if self.mailbox_factory is None:
            raise RuntimeError("Email is not configured. Set KA_IMAP_HOST, KA_IMAP_USER and KA_IMAP_PASSWORD.")
        p = job.payload
        folder = p.get("folder", "INBOX")
        limit = int(p.get("limit", 200))
        key = f"email:last_uid:{folder}"
        progress(2, "connecting")
        mailbox = self.mailbox_factory()
        try:
            with self.sf() as s:
                last_uid = int(SettingRepository(s).get(key, "0") or 0)
            uids = mailbox.uids_after(folder, last_uid)[:limit]
            if not uids:
                progress(100, "nothing new")
                return {"new": 0, "skipped": 0, "last_uid": last_uid}
            created = skipped = 0
            for i, uid in enumerate(uids):
                doc = parse_email(uid, mailbox.fetch(folder, uid))
                with self.sf() as s, s.begin():
                    repo = self._entries(s)
                    if not doc.text.strip() or repo.get_by_source_ref(doc.message_id) is not None:
                        skipped += 1
                    else:
                        repo.create(title=doc.title, content=doc.content, topic_id=p.get("topic_id"), source="email",
                                    tags=p.get("tags") or ["email"], source_ref=doc.message_id)
                        created += 1
                    SettingRepository(s).set(key, str(uid))  # advance per message so a crash resumes, not restarts
                progress(5 + int(90 * (i + 1) / len(uids)), f"{created} new, {skipped} skipped")
            return {"new": created, "skipped": skipped, "last_uid": uids[-1]}
        finally:
            close = getattr(mailbox, "close", None)
            if close:
                close()
