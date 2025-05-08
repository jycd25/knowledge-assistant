from __future__ import annotations

from typing import Iterator

from fastapi import Request
from sqlalchemy.orm import Session

from ..container import Container


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_session(request: Request) -> Iterator[Session]:
    """One transaction per request: commit on success, roll back on any exception."""
    c: Container = request.app.state.container
    with c.session_factory() as s:
        with s.begin():
            yield s
