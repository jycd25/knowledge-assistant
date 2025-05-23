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
    """Ingest a PDF or text/markdown file synchronously (no server needed)."""
    from .container import Container

    _log(verbose)
    settings = get_settings()
    c = Container.build(settings)
    if path.suffix.lower() == ".pdf":
        dest = settings.uploads_dir / path.name
        shutil.copy(path, dest)
        jid = c.queue.enqueue("ingest_pdf", {"path": str(dest), "title": title or path.stem, "topic_id": topic_id})
    else:
        jid = c.queue.enqueue("ingest_text", {"title": title or path.stem, "content": path.read_text(encoding="utf-8"), "topic_id": topic_id})
    c.worker.run_one()
    job = c.queue.get(jid)
    if job.status != "done":
        typer.secho(f"failed: {job.error}", fg="red")
        raise typer.Exit(1)
    typer.echo(f"ingested {path.name}: entry {job.result['entry_id']} ({job.result['chunks']} chunks)")


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


@db_app.command("path")
def db_path() -> None:
    typer.echo(get_settings().db_path)


@db_app.command("reset")
def db_reset(yes: bool = typer.Option(False, "--yes", help="skip confirmation")) -> None:
    """Delete the database and uploads. Irreversible."""
    settings = get_settings()
    if not yes and not typer.confirm(f"Delete everything under {settings.data_dir}?"):
        raise typer.Abort()
    for p in (settings.db_path, settings.db_path.with_suffix(".db-wal"), settings.db_path.with_suffix(".db-shm")):
        p.unlink(missing_ok=True)
    shutil.rmtree(settings.uploads_dir, ignore_errors=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    typer.echo("database reset")


if __name__ == "__main__":
    app()
