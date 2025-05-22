"""Request/response models. Kept flat and explicit so the TypeScript client is easy to derive."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class CategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class CategoryOut(BaseModel):
    id: str
    name: str
    description: str
    created_at: datetime
    topic_count: int = 0


class TopicIn(BaseModel):
    category_id: str
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class TopicPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class TopicOut(BaseModel):
    id: str
    category_id: str
    name: str
    description: str
    created_at: datetime
    entry_count: int = 0


class EntryIn(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1)
    topic_id: str | None = None
    tags: list[str] = []
    source: str = "manual"


class EntryPatch(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    content: str | None = None
    topic_id: str | None = None
    clear_topic: bool = False
    tags: list[str] | None = None


class EntrySummary(BaseModel):
    id: str
    title: str
    topic_id: str | None
    source: str
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    preview: str


class EntryOut(EntrySummary):
    content: str
    chunk_count: int


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=50)
    category_id: str | None = None
    topic_id: str | None = None
    mode: str = Field(default="hybrid", pattern="^(hybrid|vector|keyword)$")
    max_distance: float | None = Field(default=None, ge=0.0, le=2.0)


class SearchHitOut(BaseModel):
    chunk_id: str
    entry_id: str
    entry_title: str
    topic_id: str | None
    text: str
    score: float
    vector_rank: int | None
    keyword_rank: int | None


class AskRequest(BaseModel):
    question: str = Field(min_length=1)
    category_id: str | None = None
    topic_id: str | None = None


class JobOut(BaseModel):
    id: str
    kind: str
    label: str
    status: str
    progress: int
    message: str
    error: str | None
    result: dict
    attempts: int
    created_at: datetime
    finished_at: datetime | None


class IngestTextRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = Field(min_length=1)
    topic_id: str | None = None
    tags: list[str] = []


class NoteIn(BaseModel):
    title: str = ""
    body: str = Field(min_length=1)
    tags: list[str] = []


class NotePatch(BaseModel):
    title: str | None = None
    body: str | None = None
    processed_body: str | None = None
    tags: list[str] | None = None


class NoteOut(BaseModel):
    id: str
    title: str
    body: str
    processed_body: str | None
    tags: list[str]
    entry_id: str | None
    created_at: datetime
    updated_at: datetime


class ProcessNoteRequest(BaseModel):
    text: str = Field(min_length=1)
    user_request: str | None = None
    use_llm: bool = True


class ProcessNoteOut(BaseModel):
    title: str
    markdown: str
    tags: list[str]
    used_llm: bool
    applied_preferences: list[dict]


class NoteToEntryRequest(BaseModel):
    topic_id: str | None = None
    use_processed: bool = True


class TemplateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    body: str
    kind: str = "custom"


class TemplateOut(BaseModel):
    id: str
    name: str
    kind: str
    body: str
    created_at: datetime


class PreferenceOut(BaseModel):
    key: str
    value: str
    explanation: str
    updated_at: datetime


class PreferenceIn(BaseModel):
    key: str = Field(min_length=1, max_length=200)
    value: str
    explanation: str = ""


class PreferenceChatRequest(BaseModel):
    message: str = Field(min_length=1)


class PreferenceChatOut(BaseModel):
    action: str
    message: str
    saved: list[dict]
    suggested: list[dict]
    current: dict[str, str]


class SettingsOut(BaseModel):
    llm_provider: str
    llm_model: str
    llm_available: bool
    embedding_model: str
    embedding_dim: int
    data_dir: str
    entry_count: int
    chunk_count: int


class HealthOut(BaseModel):
    ok: bool
    version: str
    llm_provider: str
    llm_available: bool
