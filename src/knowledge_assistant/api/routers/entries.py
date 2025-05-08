from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...container import Container
from ...core.models import Chunk
from ...core.repositories import EntryRepository
from ..deps import get_container, get_session
from ..schemas import EntryIn, EntryOut, EntryPatch, EntrySummary

router = APIRouter(prefix="/entries", tags=["entries"])


def _repo(s: Session, c: Container) -> EntryRepository:
    return EntryRepository(s, c.embedder, c.settings.chunk_tokens, c.settings.chunk_overlap_tokens)


def _summary(e) -> EntrySummary:
    return EntrySummary(id=e.id, title=e.title, topic_id=e.topic_id, source=e.source, tags=e.tags,
                        created_at=e.created_at, updated_at=e.updated_at, preview=e.content[:200])


def _out(e, s: Session) -> EntryOut:
    n = s.scalar(select(func.count()).where(Chunk.entry_id == e.id)) or 0
    return EntryOut(**_summary(e).model_dump(), content=e.content, chunk_count=n)


@router.get("", response_model=list[EntrySummary])
def list_entries(topic_id: str | None = None, category_id: str | None = None, limit: int = 100, offset: int = 0,
                 s: Session = Depends(get_session), c: Container = Depends(get_container)):
    return [_summary(e) for e in _repo(s, c).list(topic_id, category_id, limit, offset)]


@router.post("", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryIn, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    # small entries are embedded inline; large documents should go through /jobs/ingest-text
    e = _repo(s, c).create(title=body.title, content=body.content, topic_id=body.topic_id, tags=body.tags, source=body.source)
    return _out(e, s)


@router.get("/{entry_id}", response_model=EntryOut)
def get_entry(entry_id: str, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    return _out(_repo(s, c).get(entry_id), s)


@router.patch("/{entry_id}", response_model=EntryOut)
def update_entry(entry_id: str, body: EntryPatch, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    topic = None if body.clear_topic else (body.topic_id if body.topic_id is not None else ...)
    e = _repo(s, c).update(entry_id, title=body.title, content=body.content, topic_id=topic, tags=body.tags)
    return _out(e, s)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(entry_id: str, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    _repo(s, c).delete(entry_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
