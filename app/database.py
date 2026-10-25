"""PostgreSQL-only database access for LazHelper.

The adapter translates the application's legacy positional SQL placeholders and
auto-increment declarations so every environment uses PostgreSQL. A validated schema
name isolates application state and automated tests without creating local DB files.
"""
from __future__ import annotations

import os
import re
from typing import Any

_AUTOINCREMENT_INSERTS = {"operation_journal", "project_workspaces", "saved_workflows"}
_SCHEMA_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,62}$")


def _database_url() -> str:
    value = (os.environ.get("DATABASE_URL") or os.environ.get("LAZHELPER_DATABASE_URL") or "").strip()
    if not value:
        raise RuntimeError(
            "DATABASE_URL is required. Configure a PostgreSQL connection before starting LazHelper."
        )
    if value.startswith("postgres://"):
        value = "postgresql://" + value[len("postgres://"):]
    if not value.startswith(("postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL connection URL.")
    return value.replace("postgresql+psycopg://", "postgresql://", 1)


def _postgres_sql(statement: str) -> str:
    """Translate legacy application SQL syntax into PostgreSQL syntax."""
    sql = re.sub(
        r"\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b",
        "BIGSERIAL PRIMARY KEY",
        statement,
        flags=re.IGNORECASE,
    )
    # Existing application queries use positional '?' placeholders and no '?' literals.
    return sql.replace("?", "%s")


class _CompatRow(dict):
    """Mapping row that also supports positional access for existing call sites."""
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


def connect(schema: str = "lazhelper", timeout: int = 10):
    """Open PostgreSQL and set a validated schema; never create a local database file."""
    if not _SCHEMA_RE.fullmatch(schema):
        raise ValueError("Database schema name is invalid.")
    url = _database_url()
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:  # pragma: no cover - broken deployment environment
        raise RuntimeError(
            "psycopg is required. Install the dependencies from requirements.txt."
        ) from exc

    raw = psycopg.connect(url, connect_timeout=timeout, row_factory=dict_row)
    try:
        with raw.cursor() as cursor:
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
            cursor.execute(f'SET search_path TO "{schema}"')
    except Exception:
        raw.close()
        raise
    return _PostgresConnection(raw)
