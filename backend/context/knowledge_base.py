from __future__ import annotations

import re
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    source_name: str
    chunk_text: str
    score: float


class KnowledgeBase:
    def __init__(self, sqlite_path: str, chunk_size: int = 700, chunk_overlap: int = 120) -> None:
        self.db_path = sqlite_path  # keep as str so :memory: works
        if sqlite_path != ":memory:":
            path = Path(sqlite_path)
            path.parent.mkdir(parents=True, exist_ok=True)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._lock = threading.Lock()
        # Single persistent connection — safer for :memory: and avoids reconnect overhead
        self._conn = sqlite3.connect(sqlite_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_db()

    def _init_db(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._conn.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
                chunk_id UNINDEXED,
                document_id UNINDEXED,
                source_name,
                chunk_text,
                tokenize='porter unicode61'
            )
            """
        )
        self._conn.commit()

    def ingest_text(self, source_name: str, text: str) -> str:
        clean = text.strip()
        if not clean:
            raise ValueError("Cannot ingest empty text")

        doc_id = str(uuid.uuid4())
        chunks = self._chunk_text(clean)

        with self._lock:
            self._conn.execute("INSERT INTO documents(id, source_name) VALUES(?, ?)", (doc_id, source_name))
            self._conn.executemany(
                "INSERT INTO chunks_fts(chunk_id, document_id, source_name, chunk_text) VALUES(?, ?, ?, ?)",
                [
                    (str(uuid.uuid4()), doc_id, source_name, chunk)
                    for chunk in chunks
                ],
            )
            self._conn.commit()
        return doc_id

    def list_documents(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT id, source_name, created_at FROM documents ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def delete_document(self, document_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            self._conn.execute("DELETE FROM chunks_fts WHERE document_id = ?", (document_id,))
            self._conn.commit()

    def search(self, query: str, top_k: int = 5) -> list[RetrievedChunk]:
        q = query.strip()
        if not q:
            return []

        fts_query = self._to_fts_query(q)
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT chunk_id, document_id, source_name, chunk_text, bm25(chunks_fts) AS score
                FROM chunks_fts
                WHERE chunks_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (fts_query, top_k),
            ).fetchall()

        return [
            RetrievedChunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                source_name=row["source_name"],
                chunk_text=row["chunk_text"],
                score=float(row["score"]) if row["score"] is not None else 0.0,
            )
            for row in rows
        ]

    def _chunk_text(self, text: str) -> list[str]:
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
        if not paragraphs:
            paragraphs = [text]

        chunks: list[str] = []
        for paragraph in paragraphs:
            chunks.extend(self._chunk_paragraph(paragraph))
        return chunks

    def _chunk_paragraph(self, paragraph: str) -> list[str]:
        if len(paragraph) <= self.chunk_size:
            return [paragraph]

        chunks: list[str] = []
        start = 0
        while start < len(paragraph):
            end = min(start + self.chunk_size, len(paragraph))
            chunks.append(paragraph[start:end])
            if end == len(paragraph):
                break
            start = max(0, end - self.chunk_overlap)
        return chunks

    @staticmethod
    def _to_fts_query(query: str) -> str:
        tokens = [t for t in re.findall(r"[\w-]+", query.lower()) if len(t) > 1]
        if not tokens:
            return '""'
        return " OR ".join(tokens)
