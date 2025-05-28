"""SQLite-backed job queue.

This is the producer/consumer contract for all slow work. Producers call `enqueue`;
the Worker claims rows with a single atomic UPDATE so two threads can never take the
same job. Swapping in Redis/huey later means re-implementing this class only.

Lifecycle: queued -> running -> done | failed.  A running job with a stale heartbeat
(process died mid-job) is reclaimed on startup: re-queued while attempts remain, else failed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session, sessionmaker

from ..core.models import Job, utcnow


class JobQueue:
    def __init__(self, session_factory: sessionmaker[Session], max_attempts: int = 3, stale_after_s: int = 300):
        self.sf = session_factory
        self.max_attempts = max_attempts
        self.stale_after = timedelta(seconds=stale_after_s)

    # -- producer side ---------------------------------------------------------
    def enqueue(self, kind: str, payload: dict | None = None) -> str:
        with self.sf() as s, s.begin():
            job = Job(kind=kind, payload=payload or {})
            s.add(job)
            s.flush()
            return job.id

    def get(self, job_id: str) -> Job | None:
        with self.sf() as s:
            return s.get(Job, job_id)

    # -- consumer side ---------------------------------------------------------
    def claim(self, kinds: list[str] | None = None) -> Job | None:
        """Atomically move the oldest queued job to running and return it."""
        now = utcnow()
        with self.sf() as s, s.begin():
            kind_sql = ""
            params: dict = {"now": now}
            if kinds:
                kind_sql = "AND kind IN (" + ",".join(f":k{i}" for i in range(len(kinds))) + ")"
                params.update({f"k{i}": k for i, k in enumerate(kinds)})
            row = s.execute(text(f"""
                UPDATE jobs SET status='running', started_at=:now, heartbeat_at=:now, attempts=attempts+1
                WHERE id = (SELECT id FROM jobs WHERE status='queued' {kind_sql} ORDER BY created_at LIMIT 1)
                RETURNING id
            """), params).fetchone()
            if row is None:
                return None
            job = s.get(Job, row[0])
            s.expunge(job)
            return job

    def progress(self, job_id: str, percent: int, message: str = "") -> None:
        with self.sf() as s, s.begin():
            s.execute(text("UPDATE jobs SET progress=:p, message=:m, heartbeat_at=:h WHERE id=:id"),
                      {"p": max(0, min(100, percent)), "m": message, "h": utcnow(), "id": job_id})

    def complete(self, job_id: str, result: dict | None = None) -> None:
        with self.sf() as s, s.begin():
            job = s.get(Job, job_id)
            if job:
                job.status, job.progress, job.result, job.finished_at = "done", 100, result or {}, utcnow()

    def fail(self, job_id: str, error: str) -> None:
        """Retry while attempts remain, otherwise mark failed."""
        with self.sf() as s, s.begin():
            job = s.get(Job, job_id)
            if not job:
                return
            if job.attempts < self.max_attempts:
                job.status, job.message, job.error = "queued", f"retrying after error (attempt {job.attempts})", error
            else:
                job.status, job.error, job.finished_at = "failed", error, utcnow()

    def reclaim_stale(self) -> int:
        """Called at startup: jobs left 'running' by a dead process get re-queued or failed."""
        cutoff = utcnow() - self.stale_after
        with self.sf() as s, s.begin():
            stale = s.execute(text("SELECT id, attempts FROM jobs WHERE status='running' AND (heartbeat_at IS NULL OR heartbeat_at < :c)"),
                              {"c": cutoff}).fetchall()
            for job_id, attempts in stale:
                if attempts < self.max_attempts:
                    s.execute(text("UPDATE jobs SET status='queued', message='recovered after restart' WHERE id=:id"), {"id": job_id})
                else:
                    s.execute(text("UPDATE jobs SET status='failed', error='abandoned after restart', finished_at=:f WHERE id=:id"),
                              {"id": job_id, "f": utcnow()})
            return len(stale)
