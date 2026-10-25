from app import database


def test_local_database_falls_back_to_sqlite(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("LAZHELPER_DATABASE_URL", raising=False)
    connection = database.connect(tmp_path / "state.sqlite3")
    try:
        connection.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT)")
        cursor = connection.execute("INSERT INTO sample(value) VALUES(?)", ("saved",))
        assert cursor.lastrowid == 1
        row = connection.execute("SELECT value FROM sample WHERE id=?", (1,)).fetchone()
        assert row["value"] == "saved"
    finally:
        connection.close()


def test_postgres_sql_translates_existing_sqlite_syntax():
    statement = database._postgres_sql(
        "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, value TEXT)"
    )
    assert "BIGSERIAL PRIMARY KEY" in statement
    assert "AUTOINCREMENT" not in statement

    query = database._postgres_sql("SELECT value FROM events WHERE id=?")
    assert query == "SELECT value FROM events WHERE id=%s"


def test_database_url_normalizes_legacy_postgres_scheme(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@host:5432/app")
    assert database._database_url() == "postgresql://user:pass@host:5432/app"
