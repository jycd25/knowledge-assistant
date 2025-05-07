import pytest
from sqlalchemy import text

from knowledge_assistant.core.errors import NotFoundError
from knowledge_assistant.core.repositories import EntryRepository


def test_entry_update_content_reindexes(session, embedder):
    entries = EntryRepository(session, embedder, chunk_tokens=50, overlap_tokens=5)
    e = entries.create(title="X", content="short")
    assert session.scalar(text("select count(*) from chunks")) == 1
    entries.update(e.id, content="longer text here. " * 60)
    n = session.scalar(text("select count(*) from chunks"))
    assert n > 1
    assert session.scalar(text("select count(*) from chunks_vec")) == n
    # fts trigger kept in sync
    assert session.scalar(text("select count(*) from chunks_fts")) == n


def test_entry_requires_existing_topic(session, embedder):
    entries = EntryRepository(session, embedder)
    with pytest.raises(NotFoundError):
        entries.create(title="x", content="y", topic_id="missing")
