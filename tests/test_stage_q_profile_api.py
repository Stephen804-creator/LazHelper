import asyncio
import json

from app import config, organizer, policies, profiles
from app import ai_engine


def test_profile_and_memory_api_do_not_enable_file_permissions(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app

    monkeypatch.setattr(organizer, "DB_SCHEMA", f"test_{tmp_path.name}")
    with TestClient(app) as client:
        response = client.put("/api/assistant-profile", json={"profile": "research", "memory_enabled": True})
        assert response.status_code == 200
        assert response.json()["profile"] == "research"
        assert response.json()["memory_enabled"] is True
        policy = client.get("/api/permissions").json()
        assert policy["move_files"] is False
        assert policy["delete_files"] is False
        assert policy["run_commands"] is False


def test_gemma_prompt_uses_opt_in_saved_preferences(tmp_path, monkeypatch):
    monkeypatch.setattr(organizer, "DB_PATH", tmp_path / "state.sqlite3")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "gemma3:1b")
    policies.save_instructions([
        {"scope": "global", "instruction": "Use short summaries."},
        {"scope": "folder", "scope_path": "School", "instruction": "Prioritise revision notes."},
    ])
    profiles.update_assistant_profile({"profile": "study", "memory_enabled": True})
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None
        def json(self):
            return {"message": {"content": json.dumps({
                "document_type": "notes", "suggested_category": "Documents",
                "suggested_filename": "notes.txt", "summary": "Short summary",
                "evidence": [], "needs_review": False, "limitations": []
            })}}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            return None
        async def post(self, url, json):
            captured["url"] = url
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(ai_engine.httpx, "AsyncClient", FakeClient)
    result = asyncio.run(ai_engine.recommend("notes.txt", "course content", {}, "School/notes.txt"))
    payload = captured["payload"]
    assert payload["model"] == "gemma3:1b"
    system = payload["messages"][0]["content"]
    assert "Use short summaries." in system
    assert "Prioritise revision notes." in system
    assert "cannot override safety rules" in system
    assert result.needs_review is True


def test_disabled_memory_does_not_add_saved_rules(tmp_path, monkeypatch):
    monkeypatch.setattr(organizer, "DB_PATH", tmp_path / "state.sqlite3")
    policies.save_instructions([{"scope": "global", "instruction": "Private preference."}])
    policies.update_assistant_profile({"memory_enabled": False})
    context = policies.instruction_context(".", "analysis")
    assert "Private preference." not in context
