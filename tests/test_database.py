import pytest

from app import database


def test_database_requires_postgres_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LAZHELPER_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        database.connect()


def test_postgres_sql_translates_legacy_schema_and_placeholders():
    statement = database._postgres_sql(
        "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT)"
    )
    assert "BIGSERIAL PRIMARY KEY" in statement
    assert "AUTOINCREMENT" not in statement

    query = database._postgres_sql("SELECT value FROM events WHERE id=?")
    assert query == "SELECT value FROM events WHERE id=%s"


def test_database_url_normalizes_postgres_scheme(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/app")
    assert database._database_url() == "postgresql://user:pass@host:5432/app"


def test_database_rejects_invalid_schema(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host/app")
    with pytest.raises(ValueError, match="schema name is invalid"):
        database.connect(schema="bad-schema")


def test_database_rejects_non_postgres_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "mysql://user:pass@host/app")
    with pytest.raises(RuntimeError, match="must be a PostgreSQL"):
        database.connect()
