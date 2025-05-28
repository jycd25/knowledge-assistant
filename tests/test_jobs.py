import threading

import pymupdf
from sqlalchemy import text

from knowledge_assistant.core.db import make_session_factory
from knowledge_assistant.core.models import utcnow
from knowledge_assistant.jobs import JobQueue, Worker
from knowledge_assistant.jobs.handlers import Handlers


def _make(engine, embedder, threads=1, max_attempts=3):
    sf = make_session_factory(engine)
    q = JobQueue(sf, max_attempts=max_attempts, stale_after_s=1)
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


def test_stale_running_jobs_are_reclaimed_on_start(engine, embedder):
    sf, q, w = _make(engine, embedder, max_attempts=3)
    jid = q.enqueue("ingest_text", {"title": "x", "content": "y"})
    dead = q.enqueue("ingest_text", {"title": "x", "content": "y"})
    with sf() as s, s.begin():
        s.execute(text("update jobs set status='running', attempts=3, heartbeat_at=:h where id=:i"), {"h": utcnow().replace(year=2000), "i": dead})
        s.execute(text("update jobs set status='running', attempts=1, heartbeat_at=:h where id=:i"), {"h": utcnow().replace(year=2000), "i": jid})
    assert q.reclaim_stale() == 2
    assert q.get(jid).status == "queued" and q.get(dead).status == "failed"


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


def _email_bytes(mid, subject, body):
    from email.message import EmailMessage
    m = EmailMessage(); m["From"] = "a@b.c"; m["Subject"] = subject; m["Message-ID"] = mid; m.set_content(body)
    return m.as_bytes()


def test_sync_email_creates_entries_dedupes_and_resumes(engine, embedder):
    from knowledge_assistant.core.email_source import FakeMailbox
    from knowledge_assistant.core.repositories import SettingRepository
    box = FakeMailbox({"INBOX": {
        10: _email_bytes("<a@x>", "Invoice March", "Please find the invoice attached. Total 120 EUR."),
        11: _email_bytes("<b@x>", "Lunch", "Lunch at noon tomorrow? " * 5),
        12: _email_bytes("<c@x>", "Empty", "   "),
    }})
    sf = make_session_factory(engine)
    q = JobQueue(sf, max_attempts=1)
    w = Worker(q, threads=1, poll_interval=0.01)
    h = Handlers(sf, embedder, 64, 8, mailbox_factory=lambda: box)
    w.register("sync_email", h.sync_email)

    jid = q.enqueue("sync_email", {"folder": "INBOX"})
    assert w.run_one()
    j = q.get(jid)
    assert j.status == "done", j.error
    assert j.result == {"new": 2, "skipped": 1, "last_uid": 12}
    with sf() as s:
        assert s.scalar(text("select count(*) from entries where source='email'")) == 2
        assert s.scalar(text("select title from entries where source_ref='<a@x>'")) == "Invoice March"
        assert SettingRepository(s).get("email:last_uid:INBOX") == "12"

    # second sync: nothing new, and an old message re-appearing (same Message-ID, new UID) is skipped
    box.messages["INBOX"][13] = _email_bytes("<a@x>", "Invoice March (fwd)", "duplicate")
    jid2 = q.enqueue("sync_email", {"folder": "INBOX"})
    w.run_one()
    assert q.get(jid2).result == {"new": 0, "skipped": 1, "last_uid": 13}
    with sf() as s:
        assert s.scalar(text("select count(*) from entries")) == 2


def test_sync_email_without_config_fails_clearly(engine, embedder):
    sf = make_session_factory(engine)
    q = JobQueue(sf, max_attempts=1)
    w = Worker(q, threads=1)
    w.register("sync_email", Handlers(sf, embedder, 64, 8).sync_email)
    jid = q.enqueue("sync_email", {})
    w.run_one()
    assert q.get(jid).status == "failed" and "KA_IMAP_HOST" in q.get(jid).error
