"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from src.main import create_app


@pytest.fixture
def client():
    """FastAPI TestClient with a fresh app per test."""
    app = create_app()
    return TestClient(app, cookies={"session_id": "123e4567-e89b-12d3-a456-426614174000"})
