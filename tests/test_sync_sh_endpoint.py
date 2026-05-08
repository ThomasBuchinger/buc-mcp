import pytest
from fastapi.testclient import TestClient

from src.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_sync_sh_returns_200(client):
    response = client.get("/sync.sh")
    assert response.status_code == 200


def test_sync_sh_starts_with_server_url(client):
    response = client.get("/sync.sh")
    assert response.text.startswith("SERVER_URL='http://testserver'")

def test_sync_sh_server_url_from_host_header(client):
    response = client.get("/sync.sh", headers={"Host": "myhost:8000"})
    assert "SERVER_URL='http://myhost:8000'" in response.text
