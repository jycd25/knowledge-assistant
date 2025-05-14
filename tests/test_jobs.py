import threading

import pymupdf
from sqlalchemy import text

from knowledge_assistant.core.db import make_session_factory
from knowledge_assistant.jobs import JobQueue, Worker
from knowledge_assistant.jobs.handlers import Handlers


def _make(engine, embedder, threads=1, max_attempts=3):
    sf = make_session_factory(engine)
    q = JobQueue(sf, max_attempts=max_attempts)
    w = Worker(q, threads=threads, poll_interval=0.01)
    h = Handlers(sf, embedder, chunk_tokens=64, overlap_tokens=8)
    w.register("ingest_text", h.ingest_text)
    w.register("ingest_pdf", h.ingest_pdf)
    w.register("reindex_entry", h.reindex_entry)
    return sf, q, w


def test_ingest_text_job_end_to_end(engine, embedder):
    sf, q, w = _make(engine, embedder)
    jid = q.enqueue("ingest_text", {"title": "T", "content": "hello world. " * 100})
    assert q.get(jid).status == "queued"
    assert w.run_one() is True
    job = q.get(jid)
    assert job.status == "done" and job.progress == 100 and job.result["chunks"] > 1
    with sf() as s:
        assert s.scalar(text("select count(*) from chunks_vec")) == job.result["chunks"]
    assert w.run_one() is False  # queue empty


def test_failing_handler_retries_then_fails(engine, embedder):
    sf, q, w = _make(engine, embedder, max_attempts=2)
    calls = []
    w.register("boom", lambda job, progress: calls.append(1) or (_ for _ in ()).throw(RuntimeError("nope")))
    jid = q.enqueue("boom")
    w.run_one()
    assert q.get(jid).status == "queued" and q.get(jid).attempts == 1  # retried
    w.run_one()
    j = q.get(jid)
    assert j.status == "failed" and "nope" in j.error and len(calls) == 2


def test_unknown_kind_is_not_claimed_by_this_worker(engine, embedder):
    sf, q, w = _make(engine, embedder)
    q.enqueue("email_sync")  # a future handler; must stay queued, not fail
    assert w.run_one() is False
    assert q.get(q.enqueue("email_sync")).status == "queued"


def test_claim_is_atomic_across_threads(engine, embedder):
    sf, q, w = _make(engine, embedder)
    seen = []
    lock = threading.Lock()
    def handler(job, progress):
        with lock:
            seen.append(job.id)
        return {}
    w.register("noop", handler)
    ids = [q.enqueue("noop") for _ in range(30)]
    w.threads = 4
    w.start()
    import time
    for _ in range(200):
        if len(seen) == 30:
            break
        time.sleep(0.02)
    w.stop()
    assert sorted(seen) == sorted(ids)  # every job exactly once


def test_ingest_pdf_job_uses_subprocess(engine, embedder, tmp_path):
    pdf = tmp_path / "doc.pdf"
    doc = pymupdf.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i + 1}. Photosynthesis converts light into chemical energy. " * 5)
    doc.save(pdf)
    sf, q, w = _make(engine, embedder)
    jid = q.enqueue("ingest_pdf", {"path": str(pdf), "title": "Bio"})
    assert w.run_one()
    j = q.get(jid)
    assert j.status == "done", j.error
    assert j.result["chunks"] >= 1 and not pdf.exists()  # deleted after ingest
    with sf() as s:
        assert s.scalar(text("select count(*) from entries where source='pdf'")) == 1


def test_ingest_pdf_bad_file_fails_cleanly(engine, embedder, tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    sf, q, w = _make(engine, embedder, max_attempts=1)
    jid = q.enqueue("ingest_pdf", {"path": str(bad)})
    w.run_one()
    j = q.get(jid)
    assert j.status == "failed" and "extraction failed" in j.error.lower()
