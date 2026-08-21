"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    """FastAPI TestClient with a fresh app per test."""
    app = create_app()
    return TestClient(app, cookies={"session_id": "test-session-123"})