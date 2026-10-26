from fastapi.testclient import TestClient

from app import config, organizer
from app.main import app


def test_task_preview_is_review_only(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "notes.txt").write_text("Cloud computing networking notes.", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"t_{abs(hash(tmp_path.name))}")
    with TestClient(app) as client:
        response = client.post("/api/commands/preview", json={
            "command": "find cloud computing notes", "relative_path": "."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["requires_confirmation"] is True
        assert "preview" in data["message"].lower()
        assert (root / "notes.txt").exists()


def test_question_returns_local_evidence_only(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "notes.txt").write_text(
        "Virtual networks connect cloud resources using isolated network ranges.", encoding="utf-8"
    )
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"t_{abs(hash(tmp_path.name))}")
    with TestClient(app) as client:
        response = client.post("/api/knowledge/ask", json={
            "question": "What do my notes say about virtual networks?", "relative_path": "."
        })
        assert response.status_code == 200
        data = response.json()
        assert data["sources"]
        assert data["files_considered"] >= 1
        assert data["files_changed"] if "files_changed" in data else True
