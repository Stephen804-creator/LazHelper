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


def test_ask_every_time_scope_requires_approval_for_reads(client, tmp_path):
    token = pair(client)
    folder = tmp_path / "workspace"
    folder.mkdir()
    target = folder / "readme.txt"
    target.write_text("local note", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "ask_every_time",
        "approval_mode": "ask_every_time",
        "grants": [{
            "id": "read-grant", "label": "workspace", "kind": "folder", "path": str(folder),
            "capabilities": ["read"],
        }],
    }))
    blocked_list = client.get("/v1/files", params={"path": str(folder)}, headers=auth(token))
    assert blocked_list.status_code == 409
    approved_list = client.get("/v1/files", params={"path": str(folder), "approved": "true"}, headers=auth(token))
    assert approved_list.status_code == 200
    blocked_read = client.get("/v1/files/content", params={"path": str(target)}, headers=auth(token))
    assert blocked_read.status_code == 409
    approved_read = client.get("/v1/files/content", params={"path": str(target), "approved": "true"}, headers=auth(token))
    assert approved_read.status_code == 200
    assert approved_read.json()["content"] == "local note"


def test_duplicate_scan_is_read_only(client, tmp_path):
    token = pair(client)
    folder = tmp_path / "workspace"
    folder.mkdir()
    first = folder / "first.txt"
    second = folder / "second.txt"
    first.write_text("same bytes", encoding="utf-8")
    second.write_text("same bytes", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "approval_mode": "ask_every_time",
        "grants": [{
            "id": "read-grant", "label": "workspace", "kind": "folder", "path": str(folder),
            "capabilities": ["read"],
        }],
    }))
    response = client.get("/v1/duplicates", params={"path": str(folder), "approved": "true"}, headers=auth(token))
    assert response.status_code == 200
    data = response.json()
    assert data["read_only"] is True
    assert data["groups"][0]["count"] == 2
    assert first.exists() and second.exists()



def test_local_assistant_uses_only_granted_text_files(client, tmp_path, monkeypatch):
    token = pair(client)
    folder = tmp_path / "Downloads"
    folder.mkdir()
    note = folder / "course-notes.txt"
    note.write_text("The private study phrase is violet river.", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "grants": [{
            "id": "downloads-read", "label": "Downloads", "kind": "folder",
            "path": str(folder), "capabilities": ["read"],
        }],
    }))
    captured = {}
    def fake_generate(prompt, json_mode=False):
        captured["prompt"] = prompt
        return "The note mentions violet river.", "test-local-model"
    monkeypatch.setattr(agent, "_local_model_generate", fake_generate)
    response = client.post(
        "/v1/assistant/ask",
        json={"path": str(folder), "question": "What phrase is in my note?", "approved": True},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["local_connector"] is True
    assert "violet river" in captured["prompt"]
    assert "violet river" in response.json()["answer"]


def test_local_assistant_requires_read_approval_in_ask_every_time(client, tmp_path, monkeypatch):
    token = pair(client)
    folder = tmp_path / "Downloads"
    folder.mkdir()
    (folder / "note.txt").write_text("private", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "ask_every_time",
        "grants": [{
            "id": "downloads-read", "label": "Downloads", "kind": "folder",
            "path": str(folder), "capabilities": ["read"],
        }],
    }))
    monkeypatch.setattr(agent, "_local_model_generate", lambda prompt, json_mode=False: ("unused", "test"))
    response = client.post(
        "/v1/assistant/ask",
        json={"path": str(folder), "question": "Summarize my note."},
        headers=auth(token),
    )
    assert response.status_code == 409


def test_local_task_plan_is_not_executed_and_rejects_unknown_sources(client, tmp_path, monkeypatch):
    token = pair(client)
    folder = tmp_path / "Downloads"
    folder.mkdir()
    source = folder / "report.txt"
    source.write_text("report", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "grants": [{
            "id": "downloads-all", "label": "Downloads", "kind": "folder",
            "path": str(folder), "capabilities": ["read", "create", "edit", "move", "rename", "delete"],
        }],
    }))
    fake = {
        "message": "Review the proposed move.",
        "operations": [
            {"action": "move", "path": str(source), "destination": str(folder / "report-renamed.txt"), "reason": "Test move"},
            {"action": "delete", "path": str(folder / "not-in-inventory.txt"), "reason": "Invalid source"},
        ],
    }
    monkeypatch.setattr(agent, "_local_model_generate", lambda prompt, json_mode=False: (__import__("json").dumps(fake), "test-local-model"))
    response = client.post(
        "/v1/assistant/plan",
        json={"path": str(folder), "command": "Rename report.txt"},
        headers=auth(token),
    )
    assert response.status_code == 200
    assert response.json()["executed"] is False
    assert len(response.json()["operations"]) == 1
    assert source.exists()
    assert not (folder / "report-renamed.txt").exists()
