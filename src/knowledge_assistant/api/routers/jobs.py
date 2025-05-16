from __future__ import annotations

import json
import time
import uuid
from typing import Iterator

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...container import Container
from ...core.repositories import JobRepository
from ..deps import get_container, get_session
from ..schemas import IngestTextRequest, JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])
MAX_PDF_BYTES = 200 * 1024 * 1024


def _label(j) -> str:
    p = j.payload or {}
    if j.kind == "ingest_pdf":
        return p.get("original_name") or p.get("title") or "PDF"
    if j.kind == "ingest_text":
        return p.get("title") or "Text"
    return j.kind


def _out(j) -> JobOut:
    return JobOut(id=j.id, kind=j.kind, label=_label(j), status=j.status, progress=j.progress, message=j.message, error=j.error,
                  result=j.result or {}, attempts=j.attempts, created_at=j.created_at, finished_at=j.finished_at)


@router.get("", response_model=list[JobOut])
def list_jobs(status_filter: str | None = None, limit: int = 50, s: Session = Depends(get_session)):
    return [_out(j) for j in JobRepository(s).list(status_filter, limit)]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, s: Session = Depends(get_session)):
    return _out(JobRepository(s).get(job_id))


@router.post("/ingest-text", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
def ingest_text(body: IngestTextRequest, c: Container = Depends(get_container)):
    jid = c.queue.enqueue("ingest_text", body.model_dump())
    return _out(c.queue.get(jid))


@router.post("/ingest-pdf", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def ingest_pdf(file: UploadFile = File(...), title: str | None = Form(None), topic_id: str | None = Form(None),
                     tags: str = Form(""), c: Container = Depends(get_container)):
    if not (file.filename or "").lower().endswith(".pdf"):
        raise HTTPException(400, "only .pdf files are accepted")
    dest = c.settings.uploads_dir / f"{uuid.uuid4().hex}.pdf"
    size = 0
    with dest.open("wb") as out:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                out.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "PDF larger than 200MB")
            out.write(chunk)
    payload = {"path": str(dest), "title": title or file.filename.rsplit(".", 1)[0], "topic_id": topic_id,
               "tags": [t.strip() for t in tags.split(",") if t.strip()], "original_name": file.filename}
    jid = c.queue.enqueue("ingest_pdf", payload)
    return _out(c.queue.get(jid))


@router.get("/{job_id}/events")
def job_events(job_id: str, c: Container = Depends(get_container)):
    """SSE stream of job state until it finishes. Polls the row; cheap for a local single-user app."""

    def gen() -> Iterator[str]:
        last = None
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            j = c.queue.get(job_id)
            if j is None:
                yield f"event: error\ndata: {json.dumps({'message': 'job not found'})}\n\n"
                return
            snap = _out(j).model_dump(mode="json")
            if snap != last:
                yield f"event: job\ndata: {json.dumps(snap)}\n\n"
                last = snap
            if j.status in ("done", "failed"):
                return
            time.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
