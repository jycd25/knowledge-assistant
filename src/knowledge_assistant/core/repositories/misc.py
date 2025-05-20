"""Notes: simple CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import NotFoundError
from ..models import Note


class NoteRepository:
    def __init__(self, session: Session):
        self.s = session

    def create(self, title: str, body: str, tags: list[str] | None = None, processed_body: str | None = None) -> Note:
        n = Note(title=title.strip() or "Untitled", body=body, tags=tags or [], processed_body=processed_body)
        self.s.add(n)
        self.s.flush()
        return n

    def get(self, note_id: str) -> Note:
        n = self.s.get(Note, note_id)
        if n is None:
            raise NotFoundError(f"note {note_id} not found")
        return n

    def list(self, limit: int = 100) -> list[Note]:
        return list(self.s.scalars(select(Note).order_by(Note.updated_at.desc()).limit(limit)))

    def update(self, note_id: str, **fields) -> Note:
        n = self.get(note_id)
        for k, v in fields.items():
            if v is not None and hasattr(n, k):
                setattr(n, k, v)
        self.s.flush()
        return n

    def delete(self, note_id: str) -> None:
        self.s.delete(self.get(note_id))
        self.s.flush()
