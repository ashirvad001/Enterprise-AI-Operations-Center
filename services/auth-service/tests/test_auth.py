from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/docs")
    assert response.status_code == 200

def test_register_mock():
    # A simple mock test ensuring the route exists and validates schema
    response = client.post("/api/v1/auth/register", json={})
    # Expecting 422 Unprocessable Entity due to missing required fields
    assert response.status_code == 422
