"""Notes, templates, preferences, settings: simple CRUD."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import ConflictError, NotFoundError
from ..models import Note, Preference, Setting, Template


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


class TemplateRepository:
    def __init__(self, session: Session):
        self.s = session

    def upsert(self, name: str, body: str, kind: str = "custom") -> Template:
        t = self.s.scalar(select(Template).where(Template.name == name))
        try:
            with self.s.begin_nested():
                if t:
                    t.body, t.kind = body, kind
                else:
                    t = Template(name=name, body=body, kind=kind)
                    self.s.add(t)
        except IntegrityError as e:
            raise ConflictError(f"template '{name}' already exists") from e
        return t

    def get(self, template_id: str) -> Template:
        t = self.s.get(Template, template_id)
        if t is None:
            raise NotFoundError(f"template {template_id} not found")
        return t

    def list(self) -> list[Template]:
        return list(self.s.scalars(select(Template).order_by(Template.name)))

    def delete(self, template_id: str) -> None:
        self.s.delete(self.get(template_id))
        self.s.flush()


class PreferenceRepository:
    def __init__(self, session: Session):
        self.s = session

    def set(self, key: str, value: str, explanation: str = "") -> Preference:
        p = self.s.get(Preference, key)
        if p:
            p.value, p.explanation = value, explanation
        else:
            p = Preference(key=key, value=value, explanation=explanation)
            self.s.add(p)
        self.s.flush()
        return p

    def get(self, key: str) -> Preference | None:
        return self.s.get(Preference, key)

    def list(self) -> list[Preference]:
        return list(self.s.scalars(select(Preference).order_by(Preference.key)))

    def delete(self, key: str) -> bool:
        p = self.s.get(Preference, key)
        if p is None:
            return False
        self.s.delete(p)
        self.s.flush()
        return True


class SettingRepository:
    def __init__(self, session: Session):
        self.s = session

    def get(self, key: str, default: str | None = None) -> str | None:
        s = self.s.get(Setting, key)
        return s.value if s else default

    def set(self, key: str, value: str) -> None:
        s = self.s.get(Setting, key)
        if s:
            s.value = value
        else:
            self.s.add(Setting(key=key, value=value))
        self.s.flush()

    def all(self) -> dict[str, str]:
        return {s.key: s.value for s in self.s.scalars(select(Setting))}
