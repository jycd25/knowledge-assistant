"""Job rows. The queue semantics (claim, heartbeat, reclaim) live in jobs/queue.py;
this is just typed access to the table."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import NotFoundError
from ..models import Job


class JobRepository:
    def __init__(self, session: Session):
        self.s = session

    def get(self, job_id: str) -> Job:
        j = self.s.get(Job, job_id)
        if j is None:
            raise NotFoundError(f"job {job_id} not found")
        return j

    def list(self, status: str | None = None, limit: int = 50) -> list[Job]:
        q = select(Job).order_by(Job.created_at.desc()).limit(limit)
        if status:
            q = q.where(Job.status == status)
        return list(self.s.scalars(q))
