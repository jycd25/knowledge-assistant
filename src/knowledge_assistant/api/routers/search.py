from __future__ import annotations

import json
from typing import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...container import Container
from ...core.qa import QAService
from ...core.search import HybridSearch
from ..deps import get_container, get_session
from ..schemas import AskRequest, SearchHitOut, SearchRequest

router = APIRouter(tags=["search"])


def _hit(h) -> SearchHitOut:
    return SearchHitOut(**h.__dict__)


@router.post("/search", response_model=list[SearchHitOut])
def search(body: SearchRequest, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    hits = HybridSearch(s, c.embedder).search(body.query, body.limit, body.category_id, body.topic_id, body.mode,
                                                 body.max_distance if body.max_distance is not None else c.settings.search_max_distance)
    return [_hit(h) for h in hits]


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/ask")
def ask(body: AskRequest, s: Session = Depends(get_session), c: Container = Depends(get_container)):
    """Server-sent events: one `sources` event, many `token` events, then `done`."""
    qa = QAService(HybridSearch(s, c.embedder), c.llm)
    hits = qa.retrieve(body.question, body.category_id, body.topic_id)

    def gen() -> Iterator[str]:
        yield _sse("sources", [_hit(h).model_dump() for h in hits])
        if not hits:
            yield _sse("token", "I couldn't find anything relevant in your knowledge base.")
            yield _sse("done", {})
            return
        for tok in qa.stream_from_hits(body.question, hits):
            yield _sse("token", tok)
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
