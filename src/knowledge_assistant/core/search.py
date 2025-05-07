"""Hybrid search: vector KNN (sqlite-vec) + BM25 keyword (FTS5), fused by reciprocal rank.

Each signal returns a ranked list of chunk ids. RRF gives a score of sum(1/(k+rank)) across
lists, so a chunk ranked well by both wins, and either alone still surfaces. This replaces
the original's fragile "semantic, then fall back to keyword if score < threshold" logic.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlite_vec import serialize_float32

from .embeddings import Embedder

RRF_K = 60
# Cosine distance (0 = identical). Measured with bge-small-en-v1.5: on-topic queries score
# 0.22-0.46, off-topic 0.48-0.58, so 0.45 sits in the gap. Other models need re-measuring.
DEFAULT_MAX_DISTANCE = 0.45


@dataclass
class SearchHit:
    chunk_id: str
    entry_id: str
    entry_title: str
    topic_id: str | None
    text: str
    score: float
    vector_rank: int | None
    keyword_rank: int | None


def _fts_query(q: str) -> str:
    # FTS5 treats punctuation as syntax; quote each term so user text can't break the query
    terms = [t.replace('"', '""') for t in q.split() if t.strip()]
    return " OR ".join(f'"{t}"' for t in terms) if terms else '""'


class HybridSearch:
    def __init__(self, session: Session, embedder: Embedder):
        self.s = session
        self.embedder = embedder

    def _scope_sql(self, category_id: str | None, topic_id: str | None) -> tuple[str, dict]:
        params: dict = {}
        if topic_id:
            params["topic_id"] = topic_id
            return "AND e.topic_id = :topic_id", params
        if category_id:
            params["category_id"] = category_id
            return "AND e.topic_id IN (SELECT id FROM topics WHERE category_id = :category_id)", params
        return "", params

    def vector_ranks(self, query: str, k: int, category_id=None, topic_id=None,
                     max_distance: float = DEFAULT_MAX_DISTANCE) -> list[str]:
        scope, params = self._scope_sql(category_id, topic_id)
        # KNN first (vec0 needs the k constraint on its own), then scope-filter the candidates.
        # Over-fetch so filtering still leaves ~k results.
        sql = f"""
            SELECT v.chunk_id FROM (
                SELECT chunk_id, distance FROM chunks_vec
                WHERE embedding MATCH :qvec AND k = :kk
            ) v
            JOIN chunks c ON c.id = v.chunk_id
            JOIN entries e ON e.id = c.entry_id
            WHERE v.distance <= :maxd {scope}
            ORDER BY v.distance
            LIMIT :k
        """
        qvec = serialize_float32(self.embedder.embed_query(query))
        rows = self.s.execute(text(sql), {"qvec": qvec, "kk": k * 4, "k": k, "maxd": max_distance, **params})
        return [r[0] for r in rows]

    def keyword_ranks(self, query: str, k: int, category_id=None, topic_id=None) -> list[str]:
        scope, params = self._scope_sql(category_id, topic_id)
        sql = f"""
            SELECT c.id FROM chunks_fts f
            JOIN chunks c ON c.rowid = f.rowid
            JOIN entries e ON e.id = c.entry_id
            WHERE chunks_fts MATCH :q {scope}
            ORDER BY bm25(chunks_fts)
            LIMIT :k
        """
        rows = self.s.execute(text(sql), {"q": _fts_query(query), "k": k, **params})
        return [r[0] for r in rows]

    def search(self, query: str, limit: int = 10, category_id: str | None = None,
               topic_id: str | None = None, mode: str = "hybrid",
               max_distance: float = DEFAULT_MAX_DISTANCE) -> list[SearchHit]:
        query = query.strip()
        if not query:
            return []
        fetch = max(limit * 3, 20)
        vec = self.vector_ranks(query, fetch, category_id, topic_id, max_distance) if mode in ("hybrid", "vector") else []
        kw = self.keyword_ranks(query, fetch, category_id, topic_id) if mode in ("hybrid", "keyword") else []

        scores: dict[str, float] = {}
        vrank = {cid: i + 1 for i, cid in enumerate(vec)}
        krank = {cid: i + 1 for i, cid in enumerate(kw)}
        for cid, r in vrank.items():
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + r)
        for cid, r in krank.items():
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + r)
        # fused score first; on ties prefer the better keyword rank (exact term matches are
        # the more precise signal), then the better vector rank
        inf = float("inf")
        top = sorted(scores.items(),
                     key=lambda kv: (-kv[1], krank.get(kv[0], inf), vrank.get(kv[0], inf)))[:limit]
        if not top:
            return []

        ids = [cid for cid, _ in top]
        placeholders = ",".join(f":id{i}" for i in range(len(ids)))
        rows = self.s.execute(
            text(f"""SELECT c.id, c.entry_id, e.title, e.topic_id, c.text
                     FROM chunks c JOIN entries e ON e.id = c.entry_id
                     WHERE c.id IN ({placeholders})"""),
            {f"id{i}": cid for i, cid in enumerate(ids)},
        )
        by_id = {r[0]: r for r in rows}
        hits = []
        for cid, score in top:
            r = by_id.get(cid)
            if r is None:
                continue
            hits.append(SearchHit(cid, r[1], r[2], r[3], r[4], score, vrank.get(cid), krank.get(cid)))
        return hits
