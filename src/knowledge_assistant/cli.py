"""`ka` command line."""

from __future__ import annotations

import logging
import shutil
import webbrowser
from pathlib import Path

import typer

from . import __version__
from .config import get_settings

app = typer.Typer(help="Knowledge Assistant — local-first knowledge base.", no_args_is_help=True)
db_app = typer.Typer(help="Database maintenance.")
app.add_typer(db_app, name="db")


def _log(verbose: bool) -> None:
    logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command()
def serve(host: str | None = None, port: int | None = None, open_browser: bool = typer.Option(False, "--open"),
          verbose: bool = False) -> None:
    """Start the API + worker + web UI."""
    import uvicorn

    from .api.app import create_app
    from .container import Container

    _log(verbose)
    settings = get_settings()
    host, port = host or settings.host, port or settings.port
    container = Container.build(settings)
    if open_browser:
        webbrowser.open(f"http://{host}:{port}")
    uvicorn.run(create_app(container), host=host, port=port, log_level="debug" if verbose else "info")


@app.command()
def ingest(path: Path, title: str | None = None, topic_id: str | None = None, verbose: bool = False) -> None:
    """Ingest a PDF or text/markdown file."""
    from .container import Container
    from .core.repositories import EntryRepository

    _log(verbose)
    settings = get_settings()
    c = Container.build(settings)
    if path.suffix.lower() == ".pdf":
        from .jobs.pdf_extract import extract_in_subprocess

        content, source = extract_in_subprocess(path), "pdf"
    else:
        content, source = path.read_text(encoding="utf-8"), "manual"
    with c.session_factory() as s, s.begin():
        repo = EntryRepository(s, c.embedder, settings.chunk_tokens, settings.chunk_overlap_tokens)
        e = repo.create(title=title or path.stem, content=content, topic_id=topic_id, source=source)
        typer.echo(f"ingested {path.name}: entry {e.id} ({len(e.chunks)} chunks)")


@app.command()
def search(query: str, limit: int = 5) -> None:
    """Search from the terminal."""
    from .container import Container
    from .core.search import HybridSearch

    c = Container.build(get_settings())
    with c.session_factory() as s:
        for h in HybridSearch(s, c.embedder).search(query, limit=limit):
            typer.secho(f"\n{h.entry_title}  (score {h.score:.3f})", bold=True)
            typer.echo(h.text[:300])


@app.command()
def ask(question: str) -> None:
    """Ask a question; the answer cites passages from your library."""
    from .container import Container
    from .core.qa import QAService
    from .core.search import HybridSearch

    c = Container.build(get_settings())
    with c.session_factory() as s:
        qa = QAService(HybridSearch(s, c.embedder), c.llm)
        hits, stream = qa.stream(question)
        for tok in stream:
            typer.echo(tok, nl=False)
        typer.echo()
        for i, h in enumerate(hits, 1):
            typer.secho(f"[{i}] {h.entry_title}", fg="cyan")


@db_app.command("path")
def db_path() -> None:
    typer.echo(get_settings().db_path)


if __name__ == "__main__":
    app()
