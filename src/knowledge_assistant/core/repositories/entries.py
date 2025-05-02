"""Entries and their chunks. Writing an entry = chunk + embed + store, in one transaction.

The vec0 table is not an ORM model; it is written with parameterised raw SQL. Vectors are
passed as sqlite-vec's compact float32 blob.
"""

from __future__ import annotations

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session, selectinload
from sqlite_vec import serialize_float32

from ..chunking import chunk_text
from ..embeddings import Embedder
from ..errors import NotFoundError
from ..models import Chunk, Entry, Topic, new_id


class EntryRepository:
    def __init__(self, session: Session, embedder: Embedder, chunk_tokens: int = 512, overlap_tokens: int = 64):
        self.s = session
        self.embedder = embedder
        self.chunk_tokens = chunk_tokens
        self.overlap_tokens = overlap_tokens

    # -- reads ---------------------------------------------------------------
    def get(self, entry_id: str, with_chunks: bool = False) -> Entry:
        q = select(Entry).where(Entry.id == entry_id)
        if with_chunks:
            q = q.options(selectinload(Entry.chunks))
        e = self.s.scalar(q)
        if e is None:
            raise NotFoundError(f"entry {entry_id} not found")
        return e

    def list(self, topic_id: str | None = None, category_id: str | None = None, limit: int = 100, offset: int = 0) -> list[Entry]:
        q = select(Entry).order_by(Entry.updated_at.desc()).limit(limit).offset(offset)
        if topic_id:
            q = q.where(Entry.topic_id == topic_id)
        elif category_id:
            q = q.join(Topic).where(Topic.category_id == category_id)
        return list(self.s.scalars(q))

    def count(self) -> int:
        return self.s.scalar(select(func.count()).select_from(Entry)) or 0

    # -- writes --------------------------------------------------------------
    def create(self, *, title: str, content: str, topic_id: str | None = None, source: str = "manual",
               tags: list[str] | None = None, embed: bool = True) -> Entry:
        if topic_id is not None and self.s.get(Topic, topic_id) is None:
            raise NotFoundError(f"topic {topic_id} not found")
        entry = Entry(title=title.strip(), content=content, topic_id=topic_id, source=source, tags=tags or [])
        self.s.add(entry)
        self.s.flush()
        if embed:
            self._reindex(entry)
        return entry

    def update(self, entry_id: str, *, title: str | None = None, content: str | None = None,
               topic_id: str | None = ..., tags: list[str] | None = None) -> Entry:  # type: ignore[assignment]
        entry = self.get(entry_id)
        if title is not None:
            entry.title = title.strip()
        if tags is not None:
            entry.tags = tags
        if topic_id is not ...:
            if topic_id is not None and self.s.get(Topic, topic_id) is None:
                raise NotFoundError(f"topic {topic_id} not found")
            entry.topic_id = topic_id
        if content is not None and content != entry.content:
            entry.content = content
            self.s.flush()
            self._reindex(entry)
        self.s.flush()
        return entry

    def delete(self, entry_id: str) -> None:
        entry = self.get(entry_id)
        self._delete_vectors(entry.id)
        self.s.delete(entry)
        self.s.flush()

    def reindex(self, entry_id: str) -> int:
        entry = self.get(entry_id)
        return self._reindex(entry)

    # -- internals -----------------------------------------------------------
    def _delete_vectors(self, entry_id: str) -> None:
        ids = list(self.s.scalars(select(Chunk.id).where(Chunk.entry_id == entry_id)))
        if ids:
            self.s.execute(text("DELETE FROM chunks_vec WHERE chunk_id = :cid"), [{"cid": cid} for cid in ids])

    def _reindex(self, entry: Entry) -> int:
        """Replace all chunks + vectors for an entry. Caller's transaction wraps it."""
        self._delete_vectors(entry.id)
        self.s.execute(delete(Chunk).where(Chunk.entry_id == entry.id))
        pieces = chunk_text(entry.content, self.chunk_tokens, self.overlap_tokens)
        if not pieces:
            return 0
        # title gives short chunks more context for retrieval
        vectors = self.embedder.embed([f"{entry.title}\n{p.text}" for p in pieces])
        for p, v in zip(pieces, vectors):
            c = Chunk(id=new_id(), entry_id=entry.id, ord=p.ord, text=p.text, token_count=p.token_count)
            self.s.add(c)
            self.s.flush()
            self.s.execute(text("INSERT INTO chunks_vec(chunk_id, embedding) VALUES (:cid, :vec)"),
                           {"cid": c.id, "vec": serialize_float32(v)})
        return len(pieces)
