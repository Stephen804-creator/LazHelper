"""Small database adapter: SQLite locally, Render PostgreSQL when DATABASE_URL is set.

The adapter preserves the application's existing sqlite-style SQL API so local
development stays unchanged while hosted state can live in one PostgreSQL database.
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path
from typing import Any

_AUTOINCREMENT_INSERTS = {"operation_journal", "project_workspaces", "saved_workflows"}


def _database_url() -> str | None:
    value = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("LAZHELPER_DATABASE_URL")
        or ""
    ).strip()
    if not value:
        return None
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    return value


def _postgres_sql(statement: str) -> str:
    """Translate the small subset of SQLite SQL syntax used by LazHelper."""
    sql = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        statement,
        flags=re.IGNORECASE,
    )
    # Application queries use positional '?' placeholders and no '?' literals.
    return sql.replace("?", "%s")


class _CompatRow(dict):
    """Mapping row that also supports SQLite-style positional access (row[0])."""
    def __getitem__(self, key):
        if isinstance(key, int):
            try:
                return list(self.values())[key]
            except IndexError:
                raise IndexError(key) from None
        return super().__getitem__(key)


def _compat_row(row):
    return _CompatRow(row) if isinstance(row, dict) else row


class _PostgresCursor:
    def __init__(self, cursor: Any):
        self._cursor = cursor
        self.lastrowid: int | None = None

    def execute(self, statement: str, parameters: tuple | list = ()):
        sql = _postgres_sql(statement)
        match = re.match(r"\s*INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)", statement, re.IGNORECASE)
        table = match.group(1).lower() if match else None
        needs_id = table in _AUTOINCREMENT_INSERTS and not re.search(r"\bRETURNING\b", sql, re.IGNORECASE)
        if needs_id:
            sql = sql.rstrip().rstrip(";") + " RETURNING id"
        self._cursor.execute(sql, tuple(parameters or ()))
        if needs_id:
            row = self._cursor.fetchone()
            self.lastrowid = int(row["id"]) if row and row.get("id") is not None else None
        return self

    def executemany(self, statement: str, parameter_sets):
        self._cursor.executemany(
            _postgres_sql(statement),
            [tuple(parameters or ()) for parameters in parameter_sets],
        )
        return self

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def fetchone(self):
        return _compat_row(self._cursor.fetchone())

    def fetchall(self):
        return [_compat_row(row) for row in self._cursor.fetchall()]

    def __iter__(self):
        return (_compat_row(row) for row in self._cursor)


class _PostgresConnection:
    def __init__(self, connection: Any):
        self._connection = connection

    def execute(self, statement: str, parameters: tuple | list = ()):
        cursor = _PostgresCursor(self._connection.cursor())
        return cursor.execute(statement, parameters)

    def executemany(self, statement: str, parameter_sets):
        cursor = _PostgresCursor(self._connection.cursor())
        return cursor.executemany(statement, parameter_sets)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            if exc_type is None:
                self.commit()
            else:
                self.rollback()
        finally:
            self.close()
        return False


def connect(sqlite_path: str | Path, timeout: int = 10):
    """Connect to PostgreSQL when DATABASE_URL is set, otherwise use local SQLite."""
    url = _database_url()
    if not url:
        connection = sqlite3.connect(sqlite_path, timeout=timeout)
        connection.row_factory = sqlite3.Row
        return connection

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - exercised only in a broken hosted install
        raise RuntimeError(
            "DATABASE_URL is configured but psycopg is not installed. "
            "Install the dependencies from requirements.txt."
        ) from exc

    raw = psycopg.connect(url, connect_timeout=timeout, row_factory=dict_row)
    return _PostgresConnection(raw)
