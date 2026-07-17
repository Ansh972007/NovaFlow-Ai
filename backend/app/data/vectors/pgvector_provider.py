"""pgvector provider — PostgreSQL + vector extension.

Requires: CREATE EXTENSION vector; table novaflow_embeddings.
Falls back gracefully when extension/table missing.
"""

from __future__ import annotations

import logging
from typing import Sequence

from sqlalchemy import text

from app.data.vectors.base import VectorStoreProvider

logger = logging.getLogger(__name__)


class PgVectorStore(VectorStoreProvider):
    name = "pgvector"

    def __init__(self, database_url: str):
        self.database_url = database_url
        self._ready = False

    def init(self) -> bool:
        if self._ready:
            return True
        try:
            from app.data.engine import create_data_engine

            engine = create_data_engine(self.database_url)
            with engine.begin() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS novaflow_embeddings (
                            chunk_id BIGINT PRIMARY KEY,
                            knowledge_id BIGINT NOT NULL,
                            file_id BIGINT NOT NULL,
                            workspace_id BIGINT,
                            embedding vector(1536) NOT NULL
                        )
                        """
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_nf_emb_kid ON novaflow_embeddings (knowledge_id)"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_nf_emb_ws ON novaflow_embeddings (workspace_id)"
                    )
                )
            self._ready = True
            return True
        except Exception as exc:
            logger.warning("pgvector unavailable: %s", exc)
            self._ready = False
            return False

    def upsert(self, rows: Sequence[tuple[int, int, int, list[float]]]) -> None:
        if not self.init() or not rows:
            return
        from app.data.engine import create_data_engine

        engine = create_data_engine(self.database_url)
        with engine.begin() as conn:
            for chunk_id, knowledge_id, file_id, emb in rows:
                vec = "[" + ",".join(str(float(x)) for x in emb) + "]"
                conn.execute(
                    text(
                        """
                        INSERT INTO novaflow_embeddings (chunk_id, knowledge_id, file_id, embedding)
                        VALUES (:cid, :kid, :fid, CAST(:emb AS vector))
                        ON CONFLICT (chunk_id) DO UPDATE SET
                          knowledge_id = EXCLUDED.knowledge_id,
                          file_id = EXCLUDED.file_id,
                          embedding = EXCLUDED.embedding
                        """
                    ),
                    {"cid": chunk_id, "kid": knowledge_id, "fid": file_id, "emb": vec},
                )

    def delete_by_file(self, file_id: int) -> None:
        if not self.init():
            return
        from app.data.engine import create_data_engine

        engine = create_data_engine(self.database_url)
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM novaflow_embeddings WHERE file_id = :fid"), {"fid": int(file_id)})

    def search(
        self,
        knowledge_id: int,
        query_vec: list[float],
        limit: int,
        *,
        workspace_id: int | None = None,
    ) -> list[tuple[int, float]]:
        if not self.init() or not query_vec:
            return []
        from app.data.engine import create_data_engine

        engine = create_data_engine(self.database_url)
        vec = "[" + ",".join(str(float(x)) for x in query_vec) + "]"
        sql = """
            SELECT chunk_id, 1 - (embedding <=> CAST(:emb AS vector)) AS score
            FROM novaflow_embeddings
            WHERE knowledge_id = :kid
            ORDER BY embedding <=> CAST(:emb AS vector)
            LIMIT :lim
        """
        with engine.connect() as conn:
            rows = conn.execute(
                text(sql),
                {"emb": vec, "kid": int(knowledge_id), "lim": int(limit)},
            ).fetchall()
        return [(int(r[0]), float(r[1])) for r in rows]
