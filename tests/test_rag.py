"""Tests for POST /api/search-rag."""

from unittest.mock import patch

from fastapi import status


class TestSearchRag:
    def test_search_success(self, client):
        mock_result = {
            "prompt": "What skills does the candidate have?",
            "session_id": "test-session-123",
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

        with patch("src.routers.rag.search_rag") as mock_search:
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
        with patch("src.routers.rag.search_rag") as mock_search:
            mock_search.side_effect = ValueError("Prompt is required.")

            response = client.post("/api/search-rag", json={"prompt": ""})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Prompt is required" in response.json()["detail"]

    def test_search_missing_prompt_field(self, client):
        response = client.post("/api/search-rag", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_server_error(self, client):
        with patch("src.routers.rag.search_rag") as mock_search:
            mock_search.side_effect = RuntimeError("LLM timeout")

            response = client.post(
                "/api/search-rag",
                json={"prompt": "What skills?"},
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "LLM timeout" in response.json()["detail"]

    def test_search_missing_session(self):
        from src.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client_no_cookie = TestClient(app)

        response = client_no_cookie.post(
            "/api/search-rag",
            json={"prompt": "What skills?"},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN