import io
import os
import sqlite3
import zipfile

import pytest

from app import config
from app.database import ConnectionAdapter
from app.extractor import _check_archive_limits
from app.scanner import (
    UnsafePath,
    ensure_workspace_directory,
    open_workspace_file,
    safe_file_path,
    safe_workspace_path,
)


def test_windows_and_backslash_paths_are_rejected(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)

    for value in (
        r"..\outside",
        r"folder\..\secret.txt",
        "C:/Windows/win.ini",
        r"C:\temp\file.txt",
        "folder/report.txt:secret",
        "NUL.txt",
    ):
        with pytest.raises(UnsafePath):
            safe_workspace_path(value)


@pytest.mark.skipif(os.name == "nt", reason="Symlink creation may require elevated Windows privileges.")
def test_file_and_directory_symlinks_are_rejected(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("private", encoding="utf-8")
    (root / "linked-file.txt").symlink_to(secret)
    (root / "linked-folder").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)

    with pytest.raises(UnsafePath):
        safe_file_path("linked-file.txt")
    with pytest.raises(UnsafePath):
        with open_workspace_file("linked-file.txt"):
            pass
    with pytest.raises(UnsafePath):
        safe_workspace_path("linked-folder")


@pytest.mark.skipif(os.name == "nt", reason="Symlink creation may require elevated Windows privileges.")
def test_directory_creation_does_not_traverse_symlink(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "linked").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)

    with pytest.raises(UnsafePath):
        ensure_workspace_directory("linked/new-folder")
    assert not (outside / "new-folder").exists()


def test_open_workspace_file_reads_regular_file_without_changing_it(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    source = root / "note.txt"
    source.write_bytes(b"unchanged")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)

    with open_workspace_file("note.txt") as stream:
        assert stream.read() == b"unchanged"
    assert source.read_bytes() == b"unchanged"


def test_archive_expansion_limit_rejects_high_compression_ratio():
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("repeated.txt", b"x" * 300_000)
    payload.seek(0)

    with pytest.raises(ValueError, match="compression ratio"):
        _check_archive_limits(payload)


def test_connection_adapter_closes_sqlite_connection():
    raw = sqlite3.connect(":memory:")
    adapter = ConnectionAdapter(raw, postgres=False)

    with adapter as connection:
        assert connection.execute("SELECT 1").fetchone()[0] == 1

    with pytest.raises(sqlite3.ProgrammingError):
        raw.execute("SELECT 1")


def test_workspace_api_requires_bearer_token(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(config, "API_TOKEN", "a" * 40)
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        assert client.get("/api/config").status_code == 401
        response = client.get(
            "/api/config",
            headers={"Authorization": "Bearer " + "a" * 40}
        )
        assert response.status_code == 200



def test_workspace_api_fails_closed_without_a_configured_token(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(config, "API_TOKEN", "")
    with TestClient(app) as client:
        assert client.get("/api/health").status_code == 200
        response = client.get("/api/config")
        assert response.status_code == 503
        assert "LAZ_HELPER_API_TOKEN" in response.json()["detail"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX named pipes are not available on Windows.")
def test_open_workspace_file_rejects_fifo_without_blocking(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    os.mkfifo(root / "pipe.txt")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)

    with pytest.raises(UnsafePath, match="regular files"):
        with open_workspace_file("pipe.txt"):
            pass


def test_workspace_api_rejects_example_placeholder_token(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    # This example token is exactly 32 characters, so length checks alone
    # would incorrectly accept the repository's own placeholder value.
    monkeypatch.setattr(config, "API_TOKEN", "replace-with-a-long-random-token")
    with TestClient(app) as client:
        response = client.get("/api/config")
        assert response.status_code == 503
