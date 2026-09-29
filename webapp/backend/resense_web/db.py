"""SQLite store (stdlib sqlite3, WAL). One connection shared by every thread behind a lock: the
statements are tiny and the app is a single process, so serialising them is simpler than a pool.
The worker subprocess never touches the database (it gets a spec file and writes files)."""
from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    source TEXT NOT NULL,
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL DEFAULT 0,
    n_frames INTEGER,
    duration_s REAL,
    topics TEXT NOT NULL DEFAULT '[]',
    default_topic TEXT,
    labels_name TEXT,
    warnings TEXT NOT NULL DEFAULT '[]',
    meta TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS presets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    overrides TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    id TEXT NOT NULL UNIQUE,
    recording_id TEXT NOT NULL,
    recording_name TEXT NOT NULL,
    preset_id TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    overrides TEXT NOT NULL DEFAULT '{}',
    options TEXT NOT NULL DEFAULT '{}',
    frames_total INTEGER,
    status TEXT NOT NULL,
    error TEXT,
    run_id TEXT,
    progress TEXT,
    pid INTEGER,
    created_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT
);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status, seq);
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    recording_id TEXT,
    recording_name TEXT NOT NULL,
    job_id TEXT,
    preset_id TEXT NOT NULL,
    preset_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    has_clouds INTEGER NOT NULL DEFAULT 0,
    cloud_frames INTEGER NOT NULL DEFAULT 0,
    source_kind TEXT NOT NULL,
    summary TEXT NOT NULL DEFAULT '{}'
);
"""


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._con = sqlite3.connect(str(self.path), check_same_thread=False, isolation_level=None,
                                    timeout=10.0)
        self._con.row_factory = sqlite3.Row
        with self._lock:
            self._con.execute("PRAGMA journal_mode=WAL")
            self._con.execute("PRAGMA synchronous=NORMAL")
            self._con.execute("PRAGMA busy_timeout=10000")
            self._con.executescript(SCHEMA)

    def execute(self, sql: str, params: tuple | dict = ()) -> int:
        """Run one statement; returns the number of changed rows."""
        with self._lock:
            cur = self._con.execute(sql, params)
            return cur.rowcount

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._con.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict[str, Any] | None:
        with self._lock:
            row = self._con.execute(sql, params).fetchone()
            return dict(row) if row is not None else None

    def scalar(self, sql: str, params: tuple | dict = ()) -> Any:
        with self._lock:
            row = self._con.execute(sql, params).fetchone()
            return None if row is None else row[0]

    @contextmanager
    def transaction(self) -> Iterator["Database"]:
        """Several statements atomically (the lock is held for the whole block)."""
        with self._lock:
            self._con.execute("BEGIN IMMEDIATE")
            try:
                yield self
            except BaseException:
                self._con.execute("ROLLBACK")
                raise
            self._con.execute("COMMIT")

    def insert(self, table: str, row: dict[str, Any]) -> None:
        cols = ", ".join(row)
        marks = ", ".join(f":{k}" for k in row)
        self.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", row)

    def update(self, table: str, key: str, row: dict[str, Any]) -> int:
        sets = ", ".join(f"{k} = :{k}" for k in row)
        return self.execute(f"UPDATE {table} SET {sets} WHERE id = :__id", {**row, "__id": key})

    def close(self) -> None:
        with self._lock:
            try:
                self._con.close()
            except sqlite3.Error:
                pass


def jload(value: str | None, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except ValueError:
        return default
