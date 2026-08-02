from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATABASE_PATH
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    source_path TEXT NOT NULL,
    destination_path TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL,
    error_message TEXT
);
CREATE INDEX IF NOT EXISTS idx_operations_batch ON operations (batch_id);
CREATE INDEX IF NOT EXISTS idx_operations_type ON operations (operation_type);
"""

OPERATION_TYPES = frozenset({"ORGANIZE", "DUPLICATE_REVIEW", "UNDO"})
STATUSES = frozenset({"SUCCESS", "FAILED"})

class Database:

    def __init__(self, db_path: Path | str = DATABASE_PATH) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self._db_path))
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA journal_mode=WAL;")
        self._connection.execute("PRAGMA foreign_keys=ON;")
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        with self._connection:
            self._connection.executescript(SCHEMA)
        logger.debug("Database initialized at %s", self._db_path)

    def close(self) -> None:
        self._connection.close()

    def record_operation(
        self,
        operation_type: str,
        source_path: Path | str,
        destination_path: Path | str,
        status: str = "SUCCESS",
        error_message: str | None = None,
        batch_id: str | None = None,
    ) -> int:
        normalized_type = operation_type.upper()
        if normalized_type not in OPERATION_TYPES:
            raise ValueError(
                f"Invalid operation type {operation_type!r}. "
                f"Valid types: {sorted(OPERATION_TYPES)}"
            )
        if status.upper() not in STATUSES:
            raise ValueError(
                f"Invalid status {status!r}. Valid statuses: {sorted(STATUSES)}"
            )

        batch = batch_id or new_batch_id()
        timestamp = utc_now_iso()
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO operations
                    (batch_id, operation_type, source_path, destination_path,
                     timestamp, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    batch,
                    normalized_type,
                    str(source_path),
                    str(destination_path),
                    timestamp,
                    status.upper(),
                    error_message,
                ),
            )
        return int(cursor.lastrowid)

    def get_latest_successful_batch(self) -> str | None:
        cursor = self._connection.execute(
            """
            SELECT batch_id FROM operations
            WHERE status = 'SUCCESS'
            ORDER BY id DESC
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        return row["batch_id"] if row else None

    def get_batch_operations(self, batch_id: str) -> list[sqlite3.Row]:
        cursor = self._connection.execute(
            """
            SELECT * FROM operations
            WHERE batch_id = ?
            ORDER BY id ASC
            """,
            (batch_id,),
        )
        return list(cursor.fetchall())

    def get_all_operations(self, limit: int = 100) -> list[sqlite3.Row]:
        cursor = self._connection.execute(
            """
            SELECT * FROM operations
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return list(cursor.fetchall())

def new_batch_id() -> str:
    return uuid.uuid4().hex[:16]

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
