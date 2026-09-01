"""Tests for POST /api/search-rag."""

from unittest.mock import patch

import requests
from fastapi import status


class TestSearchRag:
    def test_search_success(self, client):
        mock_result = {
            "prompt": "What skills does the candidate have?",
            "session_id": "123e4567-e89b-12d3-a456-426614174000",
            "model": "inclusionai/ling-3.0-flash",
            "retrieval_query": "candidate skills",
            "answer": "The candidate has Python and React skills.",
            "retrieved_chunks": [
                {
                    "document": "Skills: Python, React",
                    "metadata": {"entity_type": "SkillCategory"},
                    "distance": 0.1,
                    "score": 0.91,
                }
            ],
        }

        with patch("src.routers.ai_chat.search_rag") as mock_search:
            mock_search.return_value = mock_result

            response = client.post(
                "/api/search-rag",
                json={"prompt": "What skills does the candidate have?"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["answer"] == "The candidate has Python and React skills."
        assert len(data["retrieved_chunks"]) == 1

    def test_search_empty_prompt(self, client):
        response = client.post("/api/search-rag", json={"prompt": ""})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_missing_prompt_field(self, client):
        response = client.post("/api/search-rag", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_server_error(self, client):
        with patch("src.routers.ai_chat.search_rag") as mock_search:
            mock_search.side_effect = RuntimeError("LLM timeout")

            response = client.post(
                "/api/search-rag",
                json={"prompt": "What skills?"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to perform RAG search."

    def test_search_openrouter_rate_limit_returns_429(self, client):
        with patch("src.routers.ai_chat.search_rag") as mock_search:
            response = requests.Response()
            response.status_code = 429
            mock_search.side_effect = requests.HTTPError("Too Many Requests", response=response)

            res = client.post(
                "/api/search-rag",
                json={"prompt": "What skills?"},
            )

        assert res.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "rate limit" in res.json()["detail"].lower()

    def test_search_missing_session(self):
        from src.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client_no_cookie = TestClient(app)

        with patch("src.routers.ai_chat.search_rag") as mock_search:
            mock_search.return_value = {
                "prompt": "What skills?",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "model": "inclusionai/ling-3.0-flash",
                "retrieval_query": "what skills",
                "answer": "answer",
                "retrieved_chunks": [],
            }

            response = client_no_cookie.post(
                "/api/search-rag",
                json={"prompt": "What skills?"},
            )

        assert response.status_code == status.HTTP_200_OK
        assert response.cookies.get("session_id")
