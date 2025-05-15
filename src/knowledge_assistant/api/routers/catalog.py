from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...core.models import Entry, Topic
from ...core.repositories import CategoryRepository, TopicRepository
from ..deps import get_session
from ..schemas import CategoryIn, CategoryOut, CategoryPatch, TopicIn, TopicOut, TopicPatch

router = APIRouter(tags=["catalog"])


def _cat_out(c, counts: dict[str, int]) -> CategoryOut:
    return CategoryOut(id=c.id, name=c.name, description=c.description, created_at=c.created_at, topic_count=counts.get(c.id, 0))


def _topic_out(t, counts: dict[str, int]) -> TopicOut:
    return TopicOut(id=t.id, category_id=t.category_id, name=t.name, description=t.description,
                    created_at=t.created_at, entry_count=counts.get(t.id, 0))


@router.get("/categories", response_model=list[CategoryOut])
def list_categories(s: Session = Depends(get_session)):
    counts = dict(s.execute(select(Topic.category_id, func.count()).group_by(Topic.category_id)).all())
    return [_cat_out(c, counts) for c in CategoryRepository(s).list()]


@router.post("/categories", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(body: CategoryIn, s: Session = Depends(get_session)):
    return _cat_out(CategoryRepository(s).create(body.name, body.description), {})


@router.patch("/categories/{category_id}", response_model=CategoryOut)
def update_category(category_id: str, body: CategoryPatch, s: Session = Depends(get_session)):
    c = CategoryRepository(s).update(category_id, name=body.name, description=body.description)
    n = s.scalar(select(func.count()).where(Topic.category_id == category_id)) or 0
    return _cat_out(c, {c.id: n})


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: str, s: Session = Depends(get_session)):
    CategoryRepository(s).delete(category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/topics", response_model=list[TopicOut])
def list_topics(category_id: str | None = None, s: Session = Depends(get_session)):
    counts = dict(s.execute(select(Entry.topic_id, func.count()).where(Entry.topic_id.is_not(None)).group_by(Entry.topic_id)).all())
    return [_topic_out(t, counts) for t in TopicRepository(s).list(category_id)]


@router.post("/topics", response_model=TopicOut, status_code=status.HTTP_201_CREATED)
def create_topic(body: TopicIn, s: Session = Depends(get_session)):
    return _topic_out(TopicRepository(s).create(body.category_id, body.name, body.description), {})


@router.patch("/topics/{topic_id}", response_model=TopicOut)
def update_topic(topic_id: str, body: TopicPatch, s: Session = Depends(get_session)):
    t = TopicRepository(s).update(topic_id, name=body.name, description=body.description)
    n = s.scalar(select(func.count()).where(Entry.topic_id == topic_id)) or 0
    return _topic_out(t, {t.id: n})


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(topic_id: str, s: Session = Depends(get_session)):
    TopicRepository(s).delete(topic_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
