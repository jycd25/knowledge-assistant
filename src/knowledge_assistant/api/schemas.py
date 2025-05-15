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
