from fastapi.testclient import TestClient

from app import config, organizer
from app.main import app


def test_api_blocks_move_until_owner_enables_it(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}")
    with TestClient(app) as client:
        response = client.post("/api/organize/apply", json={
            "items": [{"source": "note.txt", "destination": "Documents/note.txt", "approved": True}]
        })
        assert response.status_code == 403
        assert response.json()["required_capability"] == "move_files"
        enabled = client.put("/api/permissions", json={"move_files": True})
        assert enabled.status_code == 200
        response = client.post("/api/organize/apply", json={
            "items": [{"source": "note.txt", "destination": "Documents/note.txt", "approved": True}]
        })
        assert response.status_code == 200
        assert (root / "Documents" / "note.txt").read_text(encoding="utf-8") == "hello"


def test_move_permission_does_not_imply_undo_permission(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "note.txt").write_text("hello", encoding="utf-8")
    monkeypatch.setattr(config, "ALLOWED_ROOT", root)
    monkeypatch.setattr(organizer, "DB_PATH", tmp_path / "state.sqlite3")
    with TestClient(app) as client:
        client.put("/api/permissions", json={"move_files": True})
        moved = client.post("/api/organize/apply", json={
            "items": [{"source": "note.txt", "destination": "Documents/note.txt", "approved": True}]
        })
        assert moved.status_code == 200
        operation_id = moved.json()["completed"][0]["id"]
        response = client.post(f"/api/journal/{operation_id}/undo")
        assert response.status_code == 403
        client.put("/api/permissions", json={"restore_moves": True})
        response = client.post(f"/api/journal/{operation_id}/undo")
        assert response.status_code == 200
        assert (root / "note.txt").exists()
