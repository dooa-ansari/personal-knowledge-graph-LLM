"""Integration test for /api/search-rag using Redis-backed session history."""

import json

from fastapi.testclient import TestClient

from src.main import create_app
from src.services import ai_chat_rag_service as service


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttl_values: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def ttl(self, key: str):
        return self.ttl_values.get(key, -2)

    def set(self, key: str, value: str, ex: int | None = None):
        self.values[key] = value
        if ex is not None:
            self.ttl_values[key] = ex


def test_search_rag_endpoint_persists_and_reuses_redis_history(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr(service, "_redis", fake_redis)

    captured_histories: list[str] = []

    def fake_rewrite(prompt: str, history: str) -> str:
        captured_histories.append(history)
        return prompt

    monkeypatch.setattr(service, "_rewrite_query", fake_rewrite)
    monkeypatch.setattr(
        service,
        "_retrieve",
        lambda _: [
            {
                "document": "Skills: Python, React",
                "metadata": {"entity_type": "SkillCategory"},
                "distance": 0.1,
                "score": 0.91,
            }
        ],
    )
    monkeypatch.setattr(service, "_answer", lambda *_: "Grounded answer")

    app = create_app()
    client = TestClient(
        app,
        cookies={"session_id": "123e4567-e89b-12d3-a456-426614174000"},
    )

    first = client.post("/api/search-rag", json={"prompt": "What skills?"})
    assert first.status_code == 200
    first_data = first.json()
    assert first_data["answer"] == "Grounded answer"

    second = client.post("/api/search-rag", json={"prompt": "And what about frontend?"})
    assert second.status_code == 200

    assert captured_histories[0] == ""
    assert "user: What skills?" in captured_histories[1]
    assert "assistant: Grounded answer" in captured_histories[1]

    key = service._session_key("123e4567-e89b-12d3-a456-426614174000")
    stored = json.loads(fake_redis.values[key])
    assert stored[-2] == {"role": "user", "content": "And what about frontend?"}
    assert stored[-1] == {"role": "assistant", "content": "Grounded answer"}
