"""Tests for POST /api/convert-resume."""

from unittest.mock import patch

from fastapi import status


class TestConvertResume:
    def test_convert_success(self, client):
        with patch("src.routers.parse_resume.convert_resume_to_rdf") as mock_convert:
            mock_convert.return_value = "/fake/path/resume.ttl"

            response = client.post("/api/convert-resume")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "RDF file generated successfully."
        assert data["rdf_file"] == "/fake/path/resume.ttl"

    def test_convert_file_not_found(self, client):
        with patch("src.routers.parse_resume.convert_resume_to_rdf") as mock_convert:
            mock_convert.side_effect = FileNotFoundError("File not found: /fake/resume.md")

            response = client.post("/api/convert-resume")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "File not found" in response.json()["detail"]

    def test_convert_server_error(self, client):
        with patch("src.routers.parse_resume.convert_resume_to_rdf") as mock_convert:
            mock_convert.side_effect = RuntimeError("Something broke")

            response = client.post("/api/convert-resume")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json()["detail"] == "Failed to convert resume to RDF."

    def test_convert_missing_session(self):
        from src.main import create_app
        from fastapi.testclient import TestClient

        app = create_app()
        client_no_cookie = TestClient(app)

        with patch("src.routers.parse_resume.convert_resume_to_rdf") as mock_convert:
            mock_convert.return_value = "/fake/path/resume.ttl"
            response = client_no_cookie.post("/api/convert-resume")

        assert response.status_code == status.HTTP_200_OK
        assert response.cookies.get("session_id")
