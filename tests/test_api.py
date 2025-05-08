import pytest
from fastapi.testclient import TestClient

from knowledge_assistant.api.app import create_app
from knowledge_assistant.config import Settings
from knowledge_assistant.container import Container
from knowledge_assistant.core.embeddings import HashEmbedder
from knowledge_assistant.core.llm.base import FakeProvider


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, embedding_dim=64, llm_provider="none")
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    container = Container.build(settings, embedder=HashEmbedder(64), llm=FakeProvider(reply="Answer [1]."))
    app = create_app(container, serve_static=False)
    with TestClient(app) as c:
        c.container = container
        yield c


def test_entries_search_and_ask_stream(client):
    e = client.post("/api/v1/entries", json={"title": "Coffee", "content": "Espresso is brewed under nine bars of pressure."})
    assert e.status_code == 201 and e.json()["chunk_count"] == 1
    hits = client.post("/api/v1/search", json={"query": "espresso pressure"}).json()
    assert hits and hits[0]["entry_title"] == "Coffee"
    assert client.post("/api/v1/search", json={"query": "zzzz", "mode": "keyword"}).json() == []

    with client.stream("POST", "/api/v1/ask", json={"question": "espresso pressure?"}) as r:
        body = "".join(r.iter_text())
    assert "event: sources" in body and "Coffee" in body
    assert "event: token" in body and "event: done" in body

    p = client.patch(f"/api/v1/entries/{e.json()['id']}", json={"content": "Longer content. " * 200})
    assert p.json()["chunk_count"] > 1
    assert client.delete(f"/api/v1/entries/{e.json()['id']}").status_code == 204
    assert client.get(f"/api/v1/entries/{e.json()['id']}").status_code == 404


def test_ask_without_llm_streams_sources_then_error_event(tmp_path):
    from knowledge_assistant.core.llm.base import NullProvider
    settings = Settings(data_dir=tmp_path, embedding_dim=64, llm_provider="none")
    container = Container.build(settings, embedder=HashEmbedder(64), llm=NullProvider())
    with TestClient(create_app(container, serve_static=False)) as c:
        c.post("/api/v1/entries", json={"title": "Coffee", "content": "Espresso needs nine bars of pressure."})
        with c.stream("POST", "/api/v1/ask", json={"question": "espresso pressure"}) as r:
            body = "".join(r.iter_text())
        assert r.status_code == 200
        assert "event: sources" in body and "Coffee" in body
        assert "event: error" in body and "KA_LLM_PROVIDER" in body
        assert "event: done" not in body
