import pytest

from knowledge_assistant.core.db import init_schema, make_engine, make_session_factory
from knowledge_assistant.core.embeddings import HashEmbedder

DIM = 64


@pytest.fixture
def embedder():
    return HashEmbedder(dim=DIM)


@pytest.fixture
def engine(tmp_path):
    e = make_engine(tmp_path / "test.db")
    init_schema(e, DIM)
    return e


@pytest.fixture
def session(engine):
    factory = make_session_factory(engine)
    with factory() as s:
        yield s
        s.rollback()
