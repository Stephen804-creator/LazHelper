from fastapi.testclient import TestClient

from app import config, organizer
from app.main import app


def test_activity_records_api_result_without_request_body(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}")
    with TestClient(app) as client:
        client.get("/api/health")
        response = client.get("/api/activity?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert any(item["path"] == "/api/health" and item["status_code"] == 200 for item in data["events"])
        assert "/api/activity" not in [item["path"] for item in data["events"]]
        assert "request bodies are not recorded" in data["privacy"]


def test_activity_retention_and_inflight_state(tmp_path, monkeypatch):
    from app import activity
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}")
    token = activity.begin("POST", "/api/analyze")
    assert token
    assert any(row["path"] == "/api/analyze" for row in activity.history()["active"])
    activity.finish(token, 200)
    result = activity.history()
    assert any(row["path"] == "/api/analyze" and row["status_code"] == 200 for row in result["events"])
