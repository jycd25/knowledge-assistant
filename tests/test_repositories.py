import pytest
from sqlalchemy import text

from knowledge_assistant.core.errors import ConflictError, NotFoundError
from knowledge_assistant.core.repositories import CategoryRepository, EntryRepository, TopicRepository


def test_category_crud_and_apostrophes(session):
    repo = CategoryRepository(session)
    cat = repo.create("O'Brien's notes", "desc")  # would have broken the original's f-string SQL
    assert repo.get(cat.id).name == "O'Brien's notes"
    repo.update(cat.id, name="Renamed")
    assert repo.get(cat.id).description == "desc"  # name-only update must not wipe description
    with pytest.raises(ConflictError):
        repo.create("Renamed")
    repo.delete(cat.id)
    with pytest.raises(NotFoundError):
        repo.get(cat.id)


def test_topic_unique_per_category(session):
    cats, topics = CategoryRepository(session), TopicRepository(session)
    a, b = cats.create("A"), cats.create("B")
    topics.create(a.id, "Same")
    topics.create(b.id, "Same")  # allowed: different category
    with pytest.raises(ConflictError):
        topics.create(a.id, "Same")
    with pytest.raises(NotFoundError):
        topics.create("nope", "x")


def test_delete_category_cascades_to_entries_chunks_vectors(session, embedder):
    cats, topics = CategoryRepository(session), TopicRepository(session)
    entries = EntryRepository(session, embedder, chunk_tokens=50, overlap_tokens=5)
    cat = cats.create("C")
    top = topics.create(cat.id, "T")
    e = entries.create(title="Doc", content="alpha beta. " * 100, topic_id=top.id)
    n_chunks = session.scalar(text("select count(*) from chunks where entry_id=:i"), {"i": e.id})
    n_vec = session.scalar(text("select count(*) from chunks_vec"))
    assert n_chunks > 1 and n_vec == n_chunks

    # delete via entries repo cleans vectors; delete via category cascades relational rows
    entries.delete(e.id)
    assert session.scalar(text("select count(*) from chunks_vec")) == 0
    entries.create(title="Doc2", content="gamma delta. " * 50, topic_id=top.id)
    cats.delete(cat.id)
    assert session.scalar(text("select count(*) from topics")) == 0
    assert session.scalar(text("select count(*) from entries")) == 0
    assert session.scalar(text("select count(*) from chunks")) == 0


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
