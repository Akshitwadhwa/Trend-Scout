from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    def init(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL,
                topic_query TEXT NOT NULL,
                title TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'General Tech',
                why_now TEXT NOT NULL,
                post_angle TEXT NOT NULL,
                confidence REAL NOT NULL,
                source_json TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                draft_text TEXT,
                draft_notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS watch_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                topic_query TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_opportunities_fingerprint ON opportunities(fingerprint)"
        )
        self._ensure_column(
            "opportunities",
            "category",
            "TEXT NOT NULL DEFAULT 'General Tech'",
        )
        self._connection.commit()

    def create_opportunity(
        self,
        *,
        topic_query: str,
        title: str,
        category: str,
        why_now: str,
        post_angle: str,
        confidence: float,
        source_posts: list[dict[str, Any]],
        fingerprint: str,
    ) -> int:
        cursor = self._connection.execute(
            """
            INSERT INTO opportunities (
                status,
                topic_query,
                title,
                category,
                why_now,
                post_angle,
                confidence,
                source_json,
                fingerprint
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "new",
                topic_query,
                title,
                category,
                why_now,
                post_angle,
                confidence,
                json.dumps(source_posts, ensure_ascii=True),
                fingerprint,
            ),
        )
        self._connection.commit()
        return int(cursor.lastrowid)

    def get_opportunity(self, opportunity_id: int) -> sqlite3.Row | None:
        cursor = self._connection.execute(
            "SELECT * FROM opportunities WHERE id = ?",
            (opportunity_id,),
        )
        return cursor.fetchone()

    def list_recent_opportunities(self) -> list[sqlite3.Row]:
        cursor = self._connection.execute(
            "SELECT * FROM opportunities ORDER BY created_at DESC LIMIT 15"
        )
        return cursor.fetchall()

    def find_existing_by_fingerprint(self, fingerprint: str) -> sqlite3.Row | None:
        cursor = self._connection.execute(
            """
            SELECT * FROM opportunities
            WHERE fingerprint = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (fingerprint,),
        )
        return cursor.fetchone()

    def save_draft(self, opportunity_id: int, draft_text: str, draft_notes: str) -> None:
        self._connection.execute(
            """
            UPDATE opportunities
            SET status = 'drafted',
                draft_text = ?,
                draft_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (draft_text, draft_notes, opportunity_id),
        )
        self._connection.commit()

    def get_topic_query(self, default_query: str) -> str:
        cursor = self._connection.execute(
            "SELECT topic_query FROM watch_config WHERE id = 1"
        )
        row = cursor.fetchone()
        return row["topic_query"] if row is not None else default_query

    def set_topic_query(self, topic_query: str) -> None:
        self._connection.execute(
            """
            INSERT INTO watch_config (id, topic_query)
            VALUES (1, ?)
            ON CONFLICT(id) DO UPDATE SET
                topic_query = excluded.topic_query,
                updated_at = CURRENT_TIMESTAMP
            """,
            (topic_query,),
        )
        self._connection.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = [
            row["name"]
            for row in self._connection.execute(f"PRAGMA table_info({table})")
        ]
        if column not in columns:
            self._connection.execute(
                f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
            )
