from __future__ import annotations

"""Local vector store (sqlite) + Ollama embeddings.

This is the shared long-term memory substrate between:
- BrainFlow (潜意识) loop
- QinWan (表意识) responses / proactive output

Design goals:
- Fully local/offline (uses Ollama localhost)
- Small, dependency-free (sqlite3 + stdlib)
- Metadata-aware filtering

API is intentionally tiny; we can evolve it later.
"""

import json
import math
import os
import sqlite3
import time
import urllib.request
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for x, y in zip(a, b):
        dot += x * y
        na += x * x
        nb += y * y
    if na <= 0 or nb <= 0:
        return -1.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


class LocalVectorStore:
    def __init__(
        self,
        db_path: str,
        ollama_base_url: str = "http://localhost:11434",
        embed_model: str = "nomic-embed-text",
    ):
        self.db_path = db_path
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.embed_model = embed_model
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS docs (
                    id TEXT PRIMARY KEY,
                    ts INTEGER NOT NULL,
                    type TEXT,
                    importance REAL,
                    text TEXT NOT NULL,
                    meta_json TEXT,
                    vec_json TEXT NOT NULL
                )
                """
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_docs_ts ON docs(ts)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_docs_type ON docs(type)")
            con.commit()

    def embed(self, text: str) -> List[float]:
        payload = json.dumps({"model": self.embed_model, "prompt": text}, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.ollama_base_url + "/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        vec = data.get("embedding")
        if not isinstance(vec, list) or not vec:
            raise RuntimeError("ollama embeddings returned empty vector")
        # normalize to floats
        return [float(x) for x in vec]

    def upsert(
        self,
        doc_id: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
        doc_type: str = "generic",
        importance: float = 0.0,
        ts: Optional[int] = None,
        vec: Optional[List[float]] = None,
    ):
        if ts is None:
            ts = int(time.time())
        if vec is None:
            vec = self.embed(text)
        meta_json = json.dumps(meta or {}, ensure_ascii=False)
        vec_json = json.dumps(vec)
        with sqlite3.connect(self.db_path) as con:
            con.execute(
                """
                INSERT INTO docs(id, ts, type, importance, text, meta_json, vec_json)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    ts=excluded.ts,
                    type=excluded.type,
                    importance=excluded.importance,
                    text=excluded.text,
                    meta_json=excluded.meta_json,
                    vec_json=excluded.vec_json
                """,
                (doc_id, int(ts), str(doc_type), float(importance), text, meta_json, vec_json),
            )
            con.commit()

    def _iter_docs(self, where: str = "", params: Tuple[Any, ...] = ()) -> Iterable[Tuple[str, int, str, float, str, Dict[str, Any], List[float]]]:
        q = "SELECT id, ts, type, importance, text, meta_json, vec_json FROM docs"
        if where:
            q += " WHERE " + where
        q += " ORDER BY ts DESC"
        with sqlite3.connect(self.db_path) as con:
            cur = con.execute(q, params)
            for row in cur:
                doc_id, ts, typ, imp, text, meta_json, vec_json = row
                try:
                    meta = json.loads(meta_json) if meta_json else {}
                except Exception:
                    meta = {}
                try:
                    vec = json.loads(vec_json) if vec_json else []
                except Exception:
                    vec = []
                yield str(doc_id), int(ts), str(typ), float(imp), str(text), meta, [float(x) for x in vec]

    def search(
        self,
        query: str,
        top_k: int = 6,
        filter_type: Optional[str] = None,
        min_importance: Optional[float] = None,
        recent_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        qvec = self.embed(query)

        where_parts = []
        params: List[Any] = []
        if filter_type:
            where_parts.append("type = ?")
            params.append(filter_type)
        if min_importance is not None:
            where_parts.append("importance >= ?")
            params.append(float(min_importance))
        if recent_seconds is not None:
            where_parts.append("ts >= ?")
            params.append(int(time.time()) - int(recent_seconds))
        where = " AND ".join(where_parts)

        scored: List[Tuple[float, Dict[str, Any]]] = []
        # We keep it simple: scan (sufficient for small-to-medium corpora).
        for doc_id, ts, typ, imp, text, meta, vec in self._iter_docs(where, tuple(params)):
            s = _cosine(qvec, vec)
            scored.append(
                (
                    s,
                    {
                        "id": doc_id,
                        "ts": ts,
                        "type": typ,
                        "importance": imp,
                        "score": s,
                        "text": text,
                        "meta": meta,
                    },
                )
            )

        scored.sort(key=lambda x: x[0], reverse=True)
        return [d for _, d in scored[: max(1, int(top_k))]]

    def delete(self, doc_id: str) -> bool:
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.execute("DELETE FROM docs WHERE id = ?", (str(doc_id),))
                con.commit()
                return cur.rowcount > 0
        except Exception:
            return False

    def prune(
        self,
        keep_newest: int = 5000,
        min_importance_keep: float = 6.0,
        max_age_seconds: int = 30 * 24 * 3600,
    ) -> Dict[str, Any]:
        """Forget low-importance, old items.

        Policy:
        - Always keep items with importance >= min_importance_keep.
        - For the rest: delete if older than max_age_seconds.
        - Also cap total rows to keep_newest newest rows.
        """
        now = int(time.time())
        deleted = 0
        try:
            with sqlite3.connect(self.db_path) as con:
                # 1) delete low-importance old
                cutoff = now - int(max_age_seconds)
                cur = con.execute(
                    "DELETE FROM docs WHERE importance < ? AND ts < ?",
                    (float(min_importance_keep), int(cutoff)),
                )
                deleted += cur.rowcount or 0

                # 2) cap by newest rows (do not touch high-importance)
                cur = con.execute("SELECT COUNT(1) FROM docs")
                total = int(cur.fetchone()[0] or 0)
                if total > int(keep_newest):
                    # delete candidates from oldest low-importance first
                    to_del = total - int(keep_newest)
                    rows = con.execute(
                        "SELECT id FROM docs WHERE importance < ? ORDER BY ts ASC LIMIT ?",
                        (float(min_importance_keep), int(to_del)),
                    ).fetchall()
                    ids = [r[0] for r in rows]
                    for _id in ids:
                        con.execute("DELETE FROM docs WHERE id = ?", (str(_id),))
                    deleted += len(ids)
                con.commit()
            return {"ok": True, "deleted": int(deleted)}
        except Exception as e:
            return {"ok": False, "error": str(e), "deleted": int(deleted)}
