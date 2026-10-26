"""Regression tests for complete local-device workflows and permission boundaries."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from laz_connector import agent
from laz_connector.store import StateStore

ORIGIN = "http://localhost:8000"


def make_client(tmp_path, monkeypatch):
    monkeypatch.setenv("LAZ_CONNECTOR_ALLOWED_ORIGINS", ORIGIN)
    agent.store = StateStore(tmp_path / "state")
    agent._pair_attempts = {}
    client = TestClient(agent.app)
    response = client.post(
        "/v1/pair",
        json={"code": agent.store.snapshot()["pairing_code"]},
        headers={"Origin": ORIGIN},
    )
    assert response.status_code == 200
    return client, {"Origin": ORIGIN, "Authorization": f"Bearer {response.json()['token']}"}


def grant(folder: Path, capabilities: list[str], grant_id: str = "test-grant") -> dict:
    return {
        "id": grant_id,
        "label": folder.name,
        "kind": "folder",
        "path": str(folder),
        "capabilities": capabilities,
    }


def test_download_listing_returns_metadata_only_and_requires_read_grant(tmp_path, monkeypatch):
    client, headers = make_client(tmp_path, monkeypatch)
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    secret = downloads / "private-note.txt"
    secret.write_text("never include this content in a directory listing", encoding="utf-8")

    denied = client.get("/v1/files", params={"path": str(downloads), "approved": "true"}, headers=headers)
    assert denied.status_code == 403

    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "grants": [grant(downloads, ["read"], "downloads-read")],
    }))
    response = client.get("/v1/files", params={"path": str(downloads)}, headers=headers)
    assert response.status_code == 200
    item = next(item for item in response.json()["items"] if item["name"] == secret.name)
    assert item["kind"] == "file"
    assert item["size_bytes"] == secret.stat().st_size
    assert "content" not in item
    assert "never include this content" not in response.text


def test_revoking_a_grant_blocks_the_next_file_listing(tmp_path, monkeypatch):
    client, headers = make_client(tmp_path, monkeypatch)
    folder = tmp_path / "Downloads"
    folder.mkdir()
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "grants": [grant(folder, ["read"], "downloads-read")],
    }))
    assert client.get("/v1/files", params={"path": str(folder)}, headers=headers).status_code == 200

    revoked = client.delete("/v1/permissions/grants/downloads-read", headers=headers)
    assert revoked.status_code == 200
    denied = client.get("/v1/files", params={"path": str(folder)}, headers=headers)
    assert denied.status_code == 403


def test_preview_execute_flow_requires_confirmation_and_records_activity(tmp_path, monkeypatch):
    client, headers = make_client(tmp_path, monkeypatch)
    folder = tmp_path / "workspace"
    folder.mkdir()
    target = folder / "welcome.txt"
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "approval_mode": "ask_every_time",
        "grants": [grant(folder, ["read", "create"])],
    }))
    payload = {"action": "create", "path": str(target), "content": "Created only after approval."}

    preview = client.post("/v1/operations/preview", json=payload, headers=headers)
    assert preview.status_code == 200
    assert preview.json()["requires_approval"] is True
    assert not target.exists()

    blocked = client.post("/v1/operations/execute", json=payload, headers=headers)
    assert blocked.status_code == 409
    assert not target.exists()

    applied = client.post("/v1/operations/execute", json={**payload, "approved": True}, headers=headers)
    assert applied.status_code == 200
    assert target.read_text(encoding="utf-8") == payload["content"]
    activity = client.get("/v1/activity?limit=20", headers=headers)
    assert activity.status_code == 200
    assert any(item["action"] == "create" and item["status"] == "completed" for item in activity.json()["items"])


def test_move_cannot_escape_granted_destination_even_with_approval(tmp_path, monkeypatch):
    client, headers = make_client(tmp_path, monkeypatch)
    source_folder = tmp_path / "authorized"
    outside_folder = tmp_path / "not-authorized"
    source_folder.mkdir()
    outside_folder.mkdir()
    source = source_folder / "report.txt"
    source.write_text("keep in authorized folder", encoding="utf-8")
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "approval_mode": "routine_auto",
        "grants": [grant(source_folder, ["read", "move"])],
    }))

    response = client.post(
        "/v1/operations/execute",
        json={"action": "move", "path": str(source), "destination": str(outside_folder / "report.txt"), "approved": True},
        headers=headers,
    )
    assert response.status_code == 403
    assert source.read_text(encoding="utf-8") == "keep in authorized folder"
    assert not (outside_folder / "report.txt").exists()


def test_local_plan_discards_create_destination_outside_selected_folder(tmp_path, monkeypatch):
    client, headers = make_client(tmp_path, monkeypatch)
    folder = tmp_path / "workspace"
    folder.mkdir()
    outside = tmp_path / "escape.txt"
    agent.store.update(lambda state: state.update({
        "scope_mode": "permitted_locations",
        "grants": [grant(folder, ["read", "create"])],
    }))
    model_output = {
        "message": "Proposed creation.",
        "operations": [{
            "action": "create",
            "path": str(outside),
            "content": "not allowed",
            "reason": "attempted path escape",
        }],
    }
    monkeypatch.setattr(
        agent, "_local_model_generate",
        lambda prompt, json_mode=False: (json.dumps(model_output), "test-model"),
    )
    response = client.post(
        "/v1/assistant/plan",
        json={"path": str(folder), "command": "Create a file outside this folder"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["operations"] == []
    assert not outside.exists()


def test_local_ai_configuration_rejects_remote_content_endpoint(monkeypatch):
    monkeypatch.setenv("LAZ_CONNECTOR_OLLAMA_URL", "https://example.com/api/generate")
    monkeypatch.setenv("LAZ_CONNECTOR_OLLAMA_MODEL", "test-model")
    from fastapi import HTTPException
    import pytest

    with pytest.raises(HTTPException) as error:
        agent._local_model_settings()
    assert error.value.status_code == 500
    assert "loopback" in error.value.detail
