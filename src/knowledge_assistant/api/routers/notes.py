from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ...container import Container
from ...core import notes as note_logic
from ...core.preferences import PreferenceService
from ...core.repositories import EntryRepository, NoteRepository, PreferenceRepository
from ..deps import get_container, get_session
from ..schemas import EntryOut, NoteIn, NoteOut, NotePatch, NoteToEntryRequest, ProcessNoteOut, ProcessNoteRequest
from .entries import _out as entry_out

router = APIRouter(prefix="/notes", tags=["notes"])


def _out(n) -> NoteOut:
    return NoteOut(id=n.id, title=n.title, body=n.body, processed_body=n.processed_body, tags=n.tags,
                   entry_id=n.entry_id, created_at=n.created_at, updated_at=n.updated_at)


@router.post("/process", response_model=ProcessNoteOut)
def process_note(body: ProcessNoteRequest, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    if body.use_llm:
        prefs = PreferenceService(PreferenceRepository(s), c.llm).as_prompt_list()
        r = note_logic.process_with_llm(body.text, c.llm, body.user_request, prefs)
    else:
        r = note_logic.process_heuristic(body.text)
    return ProcessNoteOut(title=r.title, markdown=r.markdown, tags=r.tags, used_llm=r.used_llm,
                          applied_preferences=r.applied_preferences)


@router.get("", response_model=list[NoteOut])
def list_notes(s: Session = Depends(get_session)):
    return [_out(n) for n in NoteRepository(s).list()]


@router.post("", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
def create_note(body: NoteIn, s: Session = Depends(get_session)):
    title = body.title or note_logic.extract_title(body.body)
    return _out(NoteRepository(s).create(title, body.body, body.tags))


@router.get("/{note_id}", response_model=NoteOut)
def get_note(note_id: str, s: Session = Depends(get_session)):
    return _out(NoteRepository(s).get(note_id))


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(note_id: str, body: NotePatch, s: Session = Depends(get_session)):
    return _out(NoteRepository(s).update(note_id, **body.model_dump(exclude_none=True)))


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, s: Session = Depends(get_session)):
    NoteRepository(s).delete(note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{note_id}/to-entry", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def note_to_entry(note_id: str, body: NoteToEntryRequest, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    """Promote a note into the knowledge base (chunked + embedded) and link the two."""
    notes = NoteRepository(s)
    n = notes.get(note_id)
    content = n.processed_body if body.use_processed and n.processed_body else n.body
    e = EntryRepository(s, c.embedder, c.settings.chunk_tokens, c.settings.chunk_overlap_tokens).create(
        title=n.title, content=content, topic_id=body.topic_id, source="note", tags=n.tags)
    notes.update(note_id, entry_id=e.id)
    return entry_out(e, s)
