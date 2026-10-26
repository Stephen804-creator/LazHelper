from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from laz_connector import agent
from laz_connector.store import StateStore


ORIGIN = "http://localhost:8000"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("LAZ_CONNECTOR_ALLOWED_ORIGINS", ORIGIN)
    agent.store = StateStore(tmp_path / "state")
    agent._pair_attempts = {}
    return TestClient(agent.app)


def pair(client):
    code = agent.store.snapshot()["pairing_code"]
    response = client.post("/v1/pair", json={"code": code}, headers={"Origin": ORIGIN})
    assert response.status_code == 200
    return response.json()["token"]


def auth(token):
    return {"Origin": ORIGIN, "Authorization": f"Bearer {token}"}


def test_health_identifies_connector_without_exposing_paths(client):
    response = client.get("/v1/health", headers={"Origin": ORIGIN})
    assert response.status_code == 200
    assert response.json()["identity"] == "laz-helper-local-connector"
    assert "path" not in response.json()


def test_pairing_code_is_one_time_and_token_is_origin_bound(client):
    token = pair(client)
    assert client.get("/v1/connection", headers=auth(token)).json()["connected"] is True
    old_code = "BAD-COD"
    rejected = client.post("/v1/pair", json={"code": old_code}, headers={"Origin": ORIGIN})
    assert rejected.status_code == 401
    rejected_origin = client.get("/v1/connection", headers={"Origin": "https://untrusted.example", "Authorization": f"Bearer {token}"})
    assert rejected_origin.status_code == 403


def test_no_file_access_without_a_grant(client, tmp_path):
    token = pair(client)
    folder = tmp_path / "private"
    folder.mkdir()
    response = client.get("/v1/files", params={"path": str(folder)}, headers=auth(token))
    assert response.status_code == 403


def test_routine_create_needs_capability_and_does_not_overwrite(client, tmp_path):
    token = pair(client)
    folder = tmp_path / "workspace"
    folder.mkdir()
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "approval_mode": "ask_every_time",
        "grants": [{
            "id": "grant1", "label": "workspace", "kind": "folder", "path": str(folder),
            "capabilities": ["read", "create", "edit", "move", "rename", "delete"],
        }],
    }))
    target = folder / "notes.txt"
    blocked = client.post("/v1/operations/execute", json={"action":"create","path":str(target),"content":"hello"}, headers=auth(token))
    assert blocked.status_code == 409
    assert not target.exists()

    client.put("/v1/permissions/preferences", json={"scope_mode":"permitted_locations","approval_mode":"routine_auto"}, headers=auth(token))
    created = client.post("/v1/operations/execute", json={"action":"create","path":str(target),"content":"hello"}, headers=auth(token))
    assert created.status_code == 200
    assert target.read_text(encoding="utf-8") == "hello"

    duplicate = client.post("/v1/operations/execute", json={"action":"create","path":str(target),"content":"overwrite"}, headers=auth(token))
    assert duplicate.status_code == 409
    assert target.read_text(encoding="utf-8") == "hello"


def test_delete_is_approval_gated_and_quarantined(client, tmp_path):
    token = pair(client)
    folder = tmp_path / "workspace"
    folder.mkdir()
    target = folder / "old.txt"
    target.write_text("keep recoverable", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "approval_mode": "routine_auto",
        "grants": [{
            "id": "grant1", "label": "workspace", "kind": "folder", "path": str(folder),
            "capabilities": ["read", "create", "edit", "move", "rename", "delete"],
        }],
    }))
    blocked = client.post("/v1/operations/execute", json={"action":"delete","path":str(target)}, headers=auth(token))
    assert blocked.status_code == 409
    assert target.exists()

    deleted = client.post("/v1/operations/execute", json={"action":"delete","path":str(target),"approved":True}, headers=auth(token))
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "quarantined"
    quarantined = Path(deleted.json()["quarantined_as"])
    assert quarantined.read_text(encoding="utf-8") == "keep recoverable"
    assert not target.exists()


def test_protected_system_path_is_rejected_on_posix():
    if os.name == "nt":
        pytest.skip("POSIX system path assertion")
    from laz_connector.security import UnsafePath, validate_existing_path
    with pytest.raises(UnsafePath):
        validate_existing_path("/etc", "folder")


def test_symlink_paths_are_rejected(tmp_path):
    from laz_connector.security import UnsafePath, validate_existing_path
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("Symlink creation unavailable")
    with pytest.raises(UnsafePath):
        validate_existing_path(str(link), "folder")
