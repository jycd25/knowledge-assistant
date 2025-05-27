from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ... import __version__
from ...container import Container
from ...core.models import Chunk, Entry
from ...core.preferences import PreferenceService
from ...core.repositories import PreferenceRepository, TemplateRepository
from ...core.templates import BUILTIN_TEMPLATES
from ..deps import get_container, get_session
from ..schemas import (HealthOut, PreferenceChatOut, PreferenceChatRequest, PreferenceIn, PreferenceOut,
                       SettingsOut, TemplateIn, TemplateOut)

router = APIRouter(tags=["misc"])


# -- templates -----------------------------------------------------------------
@router.get("/templates/builtin")
def builtin_templates() -> dict[str, str]:
    return BUILTIN_TEMPLATES


@router.get("/templates", response_model=list[TemplateOut])
def list_templates(s: Session = Depends(get_session)):
    return [TemplateOut(**t.__dict__) for t in TemplateRepository(s).list()]


@router.put("/templates", response_model=TemplateOut)
def upsert_template(body: TemplateIn, s: Session = Depends(get_session)):
    t = TemplateRepository(s).upsert(body.name, body.body, body.kind)
    return TemplateOut(id=t.id, name=t.name, kind=t.kind, body=t.body, created_at=t.created_at)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(template_id: str, s: Session = Depends(get_session)):
    TemplateRepository(s).delete(template_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# -- preferences ---------------------------------------------------------------
@router.get("/preferences", response_model=list[PreferenceOut])
def list_preferences(s: Session = Depends(get_session)):
    return [PreferenceOut(key=p.key, value=p.value, explanation=p.explanation, updated_at=p.updated_at)
            for p in PreferenceRepository(s).list()]


@router.put("/preferences", response_model=PreferenceOut)
def set_preference(body: PreferenceIn, s: Session = Depends(get_session)):
    p = PreferenceRepository(s).set(body.key, body.value, body.explanation)
    return PreferenceOut(key=p.key, value=p.value, explanation=p.explanation, updated_at=p.updated_at)


@router.delete("/preferences/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preference(key: str, s: Session = Depends(get_session)):
    PreferenceRepository(s).delete(key)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/preferences/chat", response_model=PreferenceChatOut)
def preference_chat(body: PreferenceChatRequest, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    r = PreferenceService(PreferenceRepository(s), c.llm).handle(body.message)
    return PreferenceChatOut(action=r.action, message=r.message, saved=r.saved, suggested=r.suggested, current=r.current)


# -- settings / health -----------------------------------------------------------
@router.get("/settings", response_model=SettingsOut)
def settings(s: Session = Depends(get_session), c: Container = Depends(get_container)):
    st = c.settings
    return SettingsOut(llm_provider=c.llm.name, llm_model=c.llm.model, llm_available=c.llm.is_available(),
                       embedding_model=st.embedding_model, embedding_dim=st.embedding_dim, data_dir=str(st.data_dir),
                       entry_count=s.scalar(select(func.count()).select_from(Entry)) or 0,
                       chunk_count=s.scalar(select(func.count()).select_from(Chunk)) or 0,
                       email_configured=st.email_configured, email_account=st.imap_user if st.email_configured else None)


@router.get("/health", response_model=HealthOut)
def health(c: Container = Depends(get_container)):
    return HealthOut(ok=True, version=__version__, llm_provider=c.llm.name, llm_available=c.llm.is_available())
