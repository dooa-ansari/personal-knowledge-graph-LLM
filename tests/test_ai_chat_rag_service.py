"""Unit tests for Redis-backed session storage in ai_chat_rag_service."""

import json

import pytest

from src import config
from src.services import ai_chat_rag_service as service


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.ttl_values: dict[str, int] = {}
        self.set_calls: list[tuple[str, str, int | None]] = []

    def get(self, key: str):
        return self.values.get(key)

    def ttl(self, key: str):
        return self.ttl_values.get(key, -2)

    def set(self, key: str, value: str, ex: int | None = None):
        self.values[key] = value
        self.set_calls.append((key, value, ex))
        if ex is not None:
            self.ttl_values[key] = ex


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(service, "_redis", client)
    return client


def test_get_session_messages_returns_empty_for_missing_session(fake_redis):
    assert service._get_session_messages("missing-session") == []


def test_get_session_messages_returns_empty_for_invalid_json(fake_redis):
    key = service._session_key("bad-json")
    fake_redis.values[key] = "not-json"

    assert service._get_session_messages("bad-json") == []


def test_save_session_messages_sets_default_ttl_for_new_session(fake_redis, monkeypatch):
    monkeypatch.setattr(config, "SESSION_TTL_SECONDS", 900)

    service._save_session_messages("new-session", [{"role": "user", "content": "hello"}])

    key, _, ex = fake_redis.set_calls[-1]
    assert key == "chat:new-session"
    assert ex == 900


def test_save_session_messages_preserves_existing_ttl(fake_redis):
    key = service._session_key("active-session")
    fake_redis.values[key] = json.dumps([])
    fake_redis.ttl_values[key] = 321

    service._save_session_messages("active-session", [{"role": "assistant", "content": "ok"}])

    _, _, ex = fake_redis.set_calls[-1]
    assert ex == 321


def test_save_session_messages_enforces_default_ttl_when_key_has_no_expiry(fake_redis, monkeypatch):
    monkeypatch.setattr(config, "SESSION_TTL_SECONDS", 900)
    key = service._session_key("no-expiry-session")
    fake_redis.values[key] = json.dumps([])
    fake_redis.ttl_values[key] = -1

    service._save_session_messages("no-expiry-session", [{"role": "user", "content": "hey"}])

    _, _, ex = fake_redis.set_calls[-1]
    assert ex == 900


def test_search_rag_uses_redis_history_and_persists_new_turn(fake_redis, monkeypatch):
    session_id = "abc123"
    key = service._session_key(session_id)
    fake_redis.values[key] = json.dumps([
        {"role": "user", "content": "first question"},
        {"role": "assistant", "content": "first answer"},
    ])
    fake_redis.ttl_values[key] = 120

    captured = {}

    def fake_rewrite(prompt: str, history: str) -> str:
        captured["history"] = history
        return prompt

    monkeypatch.setattr(service, "_rewrite_query", fake_rewrite)
    monkeypatch.setattr(service, "_retrieve", lambda _: [])
    monkeypatch.setattr(service, "_answer", lambda *_: "new answer")

    result = service.search_rag(session_id, "follow up")

    assert "user: first question" in captured["history"]
    assert "assistant: first answer" in captured["history"]
    assert result["answer"] == "new answer"

    saved_payload = json.loads(fake_redis.values[key])
    assert saved_payload[-2] == {"role": "user", "content": "follow up"}
    assert saved_payload[-1] == {"role": "assistant", "content": "new answer"}
