import io

import pymupdf
import pytest
from fastapi.testclient import TestClient

from knowledge_assistant.api.app import create_app
from knowledge_assistant.config import Settings
from knowledge_assistant.container import Container
from knowledge_assistant.core.embeddings import HashEmbedder
from knowledge_assistant.core.llm.base import FakeProvider


@pytest.fixture
def client(tmp_path):
    settings = Settings(data_dir=tmp_path, embedding_dim=64, llm_provider="none", worker_threads=1)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    container = Container.build(settings, embedder=HashEmbedder(64), llm=FakeProvider(reply="Answer [1]."))
    app = create_app(container, serve_static=False)
    with TestClient(app) as c:
        c.container = container
        yield c


def test_health_and_settings(client):
    assert client.get("/api/v1/health").json()["ok"] is True
    s = client.get("/api/v1/settings").json()
    assert s["llm_provider"] == "fake" and s["entry_count"] == 0


def test_catalog_crud_and_error_mapping(client):
    r = client.post("/api/v1/categories", json={"name": "Sci"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert client.post("/api/v1/categories", json={"name": "Sci"}).status_code == 409
    assert client.patch("/api/v1/categories/nope", json={"name": "x"}).status_code == 404
    t = client.post("/api/v1/topics", json={"category_id": cid, "name": "Physics"}).json()
    assert client.get("/api/v1/categories").json()[0]["topic_count"] == 1
    assert client.get(f"/api/v1/topics?category_id={cid}").json()[0]["id"] == t["id"]
    assert client.delete(f"/api/v1/categories/{cid}").status_code == 204
    assert client.get("/api/v1/topics").json() == []


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


def test_pdf_upload_creates_job_and_worker_completes_it(client):
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Mitochondria are the powerhouse of the cell. " * 10)
    buf = io.BytesIO(doc.tobytes())
    r = client.post("/api/v1/jobs/ingest-pdf", files={"file": ("cell.pdf", buf, "application/pdf")}, data={"tags": "bio, cells"})
    assert r.status_code == 202
    jid = r.json()["id"]
    # worker thread is running under lifespan; wait via the SSE endpoint
    with client.stream("GET", f"/api/v1/jobs/{jid}/events") as s:
        events = "".join(s.iter_text())
    assert '"status": "done"' in events, events
    j = client.get(f"/api/v1/jobs/{jid}").json()
    assert j["result"]["chunks"] >= 1
    entries = client.get("/api/v1/entries").json()
    assert entries[0]["source"] == "pdf" and entries[0]["tags"] == ["bio", "cells"]
    assert client.post("/api/v1/jobs/ingest-pdf", files={"file": ("x.txt", b"hi", "text/plain")}).status_code == 400


def test_notes_process_save_and_promote(client):
    text = "Today I learned that sourdough needs a long proof. However, the oven must be very hot. " * 3
    r = client.post("/api/v1/notes/process", json={"text": text, "use_llm": False}).json()
    assert r["markdown"].startswith("# ") and not r["used_llm"]
    r2 = client.post("/api/v1/notes/process", json={"text": text, "use_llm": True}).json()
    assert r2["used_llm"] and r2["markdown"] == "Answer [1]."
    n = client.post("/api/v1/notes", json={"body": text, "tags": ["baking"]}).json()
    assert n["title"]
    client.patch(f"/api/v1/notes/{n['id']}", json={"processed_body": r["markdown"]})
    e = client.post(f"/api/v1/notes/{n['id']}/to-entry", json={})
    assert e.status_code == 201 and e.json()["source"] == "note"
    assert client.get(f"/api/v1/notes/{n['id']}").json()["entry_id"] == e.json()["id"]


def test_templates_and_preferences(client):
    assert set(client.get("/api/v1/templates/builtin").json()) == {"basic", "meeting", "project", "research", "study"}
    t = client.put("/api/v1/templates", json={"name": "Mine", "body": "# x"}).json()
    assert client.put("/api/v1/templates", json={"name": "Mine", "body": "# y"}).json()["body"] == "# y"
    assert client.delete(f"/api/v1/templates/{t['id']}").status_code == 204
    client.put("/api/v1/preferences", json={"key": "style", "value": "casual"})
    assert client.get("/api/v1/preferences").json()[0]["value"] == "casual"
    client.container.llm.reply = '{"request_type":"list_preferences","confidence":99}'
    assert client.post("/api/v1/preferences/chat", json={"message": "show"}).json()["current"] == {"style": "casual"}
    assert client.delete("/api/v1/preferences/style").status_code == 204


def test_ask_without_llm_streams_sources_then_error_event(tmp_path):
    from knowledge_assistant.core.llm.base import NullProvider
    settings = Settings(data_dir=tmp_path, embedding_dim=64, llm_provider="none", worker_threads=1)
    container = Container.build(settings, embedder=HashEmbedder(64), llm=NullProvider())
    with TestClient(create_app(container, serve_static=False)) as c:
        c.post("/api/v1/entries", json={"title": "Coffee", "content": "Espresso needs nine bars of pressure."})
        with c.stream("POST", "/api/v1/ask", json={"question": "espresso pressure"}) as r:
            body = "".join(r.iter_text())
        assert r.status_code == 200
        assert "event: sources" in body and "Coffee" in body
        assert "event: error" in body and "KA_LLM_PROVIDER" in body
        assert "event: done" not in body
