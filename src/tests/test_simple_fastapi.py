from fastapi.testclient import TestClient

# Ensure project root is on sys.path so tests can import the application module.
import sys
import os
from pathlib import Path

# Add the src directory to sys.path for absolute imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from minecraft_mcp_server.mcp_client import app

client = TestClient(app)


def test_ping_endpoint() -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"message": "pong"}