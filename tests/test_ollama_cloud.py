import asyncio
import json

from app import ai_engine, config, profiles


def test_chat_endpoint_accepts_cloud_api_base_and_host():
    assert ai_engine._chat_endpoint("https://ollama.com/api") == "https://ollama.com/api/chat"
    assert ai_engine._chat_endpoint("https://ollama.com") == "https://ollama.com/api/chat"
    assert ai_engine._chat_endpoint("http://127.0.0.1:11434") == "http://127.0.0.1:11434/api/chat"


def test_recommend_sends_cloud_bearer_key_and_gemma_model(monkeypatch):
    calls = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {
                    "content": json.dumps({
                        "document_type": "Report",
                        "suggested_category": "Work",
                        "suggested_filename": "summary.txt",
                        "summary": "A short test report.",
                        "evidence": ["test excerpt"],
                        "needs_review": True,
                        "limitations": [],
                    })
                }
            }

    class FakeAsyncClient:
        def __init__(self, timeout):
            calls["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, *, json, headers):
            calls["url"] = url
            calls["payload"] = json
            calls["headers"] = headers
            return FakeResponse()

    monkeypatch.setattr(ai_engine.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(profiles, "instruction_context", lambda *_args: "Test profile")
    monkeypatch.setattr(config, "OLLAMA_URL", "https://ollama.com/api")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "gemma4:31b")
    monkeypatch.setattr(config, "OLLAMA_API_KEY", "test-secret")
    monkeypatch.setattr(config, "AI_TIMEOUT_SECONDS", 5)

    recommendation = asyncio.run(
        ai_engine.recommend("report.txt", "sample content", "plain text", ".")
    )

    assert calls["url"] == "https://ollama.com/api/chat"
    assert calls["headers"] == {"Authorization": "Bearer test-secret"}
    assert calls["payload"]["model"] == "gemma4:31b"
    assert recommendation.suggested_filename == "summary.txt"
    assert recommendation.needs_review is True
