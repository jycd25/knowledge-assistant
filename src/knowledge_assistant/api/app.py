"""FastAPI application factory. Serves the API under /api/v1 and the built SPA at /."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..container import Container
from ..core.errors import ConflictError, NotFoundError
from ..core.llm import LLMUnavailable
from .routers import catalog, entries, jobs, misc, notes, search

log = logging.getLogger(__name__)
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def create_app(container: Container, serve_static: bool = True) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container.start()
        log.info("worker started; llm=%s data=%s", container.llm.name, container.settings.data_dir)
        try:
            yield
        finally:
            container.stop()

    app = FastAPI(title="Knowledge Assistant", version="0.1.0", lifespan=lifespan)
    app.state.container = container

    api = FastAPI(title="Knowledge Assistant API")
    for r in (catalog.router, entries.router, search.router, jobs.router, notes.router, misc.router):
        api.include_router(r)

    @api.exception_handler(NotFoundError)
    async def _nf(_: Request, e: NotFoundError):
        return JSONResponse({"detail": str(e)}, status_code=404)

    @api.exception_handler(ConflictError)
    async def _cf(_: Request, e: ConflictError):
        return JSONResponse({"detail": str(e)}, status_code=409)

    @api.exception_handler(LLMUnavailable)
    async def _llm(_: Request, e: LLMUnavailable):
        return JSONResponse({"detail": str(e)}, status_code=503)

    api.state.container = container
    app.mount("/api/v1", api)

    if serve_static and STATIC_DIR.exists():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        async def spa(path: str):
            target = STATIC_DIR / path
            if path and target.is_file():
                return FileResponse(target)
            return FileResponse(STATIC_DIR / "index.html")

    return app
