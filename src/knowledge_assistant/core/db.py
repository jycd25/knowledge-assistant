"""Database engine setup.

One SQLite file holds everything: relational tables (SQLAlchemy ORM), a sqlite-vec
virtual table for embeddings, and an FTS5 table for keyword search. The vec/fts
tables are created here with raw SQL because SQLAlchemy has no notion of them.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import sqlite_vec
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from .models import Base


def _on_connect(dbapi_conn: sqlite3.Connection, _record) -> None:
    dbapi_conn.enable_load_extension(True)
    sqlite_vec.load(dbapi_conn)
    dbapi_conn.enable_load_extension(False)
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode = WAL")
    cur.execute("PRAGMA synchronous = NORMAL")
    cur.execute("PRAGMA busy_timeout = 5000")
    cur.close()


def make_engine(db_path: Path | str) -> Engine:
    url = "sqlite://" if str(db_path) == ":memory:" else f"sqlite:///{db_path}"
    engine = create_engine(url, future=True)
    event.listen(engine, "connect", _on_connect)
    return engine


VEC_DDL = "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_vec USING vec0(chunk_id TEXT PRIMARY KEY, embedding float[{dim}] distance_metric=cosine)"

FTS_DDL = [
    "CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(text, content='chunks', content_rowid='rowid')",
    # keep the FTS index in sync with the chunks table
    """CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
         INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text);
       END""",
    """CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
         INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
       END""",
    """CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
         INSERT INTO chunks_fts(chunks_fts, rowid, text) VALUES ('delete', old.rowid, old.text);
         INSERT INTO chunks_fts(rowid, text) VALUES (new.rowid, new.text);
       END""",
]


def init_schema(engine: Engine, embedding_dim: int) -> None:
    """Create all tables. Idempotent. Alembic owns changes after v1; this is the bootstrap."""
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text(VEC_DDL.format(dim=embedding_dim)))
        for ddl in FTS_DDL:
            conn.execute(text(ddl))


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(engine, expire_on_commit=False, future=True)
