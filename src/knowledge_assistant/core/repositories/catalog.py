"""Categories and topics. Cascading deletes are enforced by the database, not by loops."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import ConflictError, NotFoundError
from ..models import Category, Topic


class CategoryRepository:
    def __init__(self, session: Session):
        self.s = session

    def create(self, name: str, description: str = "") -> Category:
        cat = Category(name=name.strip(), description=description)
        try:
            with self.s.begin_nested():
                self.s.add(cat)
        except IntegrityError as e:
            raise ConflictError(f"category '{name}' already exists") from e
        return cat

    def get(self, category_id: str) -> Category:
        cat = self.s.get(Category, category_id)
        if cat is None:
            raise NotFoundError(f"category {category_id} not found")
        return cat

    def list(self) -> list[Category]:
        return list(self.s.scalars(select(Category).order_by(Category.name)))

    def update(self, category_id: str, *, name: str | None = None, description: str | None = None) -> Category:
        cat = self.get(category_id)
        try:
            with self.s.begin_nested():
                if name is not None:
                    cat.name = name.strip()
                if description is not None:
                    cat.description = description
        except IntegrityError as e:
            raise ConflictError(f"category '{name}' already exists") from e
        return cat

    def delete(self, category_id: str) -> None:
        self.s.delete(self.get(category_id))
        self.s.flush()


class TopicRepository:
    def __init__(self, session: Session):
        self.s = session

    def create(self, category_id: str, name: str, description: str = "") -> Topic:
        if self.s.get(Category, category_id) is None:
            raise NotFoundError(f"category {category_id} not found")
        topic = Topic(category_id=category_id, name=name.strip(), description=description)
        try:
            with self.s.begin_nested():
                self.s.add(topic)
        except IntegrityError as e:
            raise ConflictError(f"topic '{name}' already exists in this category") from e
        return topic

    def get(self, topic_id: str) -> Topic:
        t = self.s.get(Topic, topic_id)
        if t is None:
            raise NotFoundError(f"topic {topic_id} not found")
        return t

    def list(self, category_id: str | None = None) -> list[Topic]:
        q = select(Topic).order_by(Topic.name)
        if category_id:
            q = q.where(Topic.category_id == category_id)
        return list(self.s.scalars(q))

    def update(self, topic_id: str, *, name: str | None = None, description: str | None = None) -> Topic:
        t = self.get(topic_id)
        try:
            with self.s.begin_nested():
                if name is not None:
                    t.name = name.strip()
                if description is not None:
                    t.description = description
        except IntegrityError as e:
            raise ConflictError(f"topic '{name}' already exists in this category") from e
        return t

    def delete(self, topic_id: str) -> None:
        self.s.delete(self.get(topic_id))
        self.s.flush()
