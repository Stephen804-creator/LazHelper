"""Database connections for local SQLite and deployed PostgreSQL environments."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from . import config

DB_PATH = config.PROJECT_ROOT / ".lazydesk_state.sqlite3"


class ConnectionAdapter:
    """Keep the small SQL surface used by Laz Helper consistent across drivers."""

    def __init__(self, connection: Any, postgres: bool):
        self.connection = connection
        self.postgres = postgres

    def execute(self, query: str, parameters=()):
        if self.postgres:
            query = query.replace("?", "%s")
        return self.connection.execute(query, parameters)

    def commit(self):
        return self.connection.commit()

    def close(self):
        return self.connection.close()

    def __enter__(self):
        self.connection.__enter__()
        return self

    def __exit__(self, exc_type, exc, traceback):
        return self.connection.__exit__(exc_type, exc, traceback)


def connect() -> ConnectionAdapter:
    """Connect to DATABASE_URL when configured; otherwise use local SQLite."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL is configured but the psycopg driver is unavailable. "
                "Install the project requirements and redeploy."
            ) from exc

        # Render and some providers supply the legacy postgres:// scheme.
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        raw = psycopg.connect(
            database_url,
            row_factory=dict_row,
            connect_timeout=10,
            application_name="laz-helper",
        )
        con = ConnectionAdapter(raw, postgres=True)
        con.execute("""CREATE TABLE IF NOT EXISTS operation_journal (
            id BIGSERIAL PRIMARY KEY, action TEXT NOT NULL,
            source_path TEXT NOT NULL, destination_path TEXT, status TEXT NOT NULL,
            created_at TEXT NOT NULL, undone_at TEXT, detail TEXT
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS review_queue (
            path TEXT PRIMARY KEY, reason TEXT NOT NULL, added_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open'
        )""")
        con.commit()
        return con

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(DB_PATH, timeout=10)
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA journal_mode=WAL")
    con = ConnectionAdapter(raw, postgres=False)
    con.execute("""CREATE TABLE IF NOT EXISTS operation_journal (
        id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL,
        source_path TEXT NOT NULL, destination_path TEXT, status TEXT NOT NULL,
        created_at TEXT NOT NULL, undone_at TEXT, detail TEXT
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS preferences (
        key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS review_queue (
        path TEXT PRIMARY KEY, reason TEXT NOT NULL, added_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'open'
    )""")
    con.commit()
    return con
