import pytest


@pytest.mark.anyio
async def test_liveness(http_client):
    response = await http_client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_readiness(http_client):
    response = await http_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.anyio
async def test_metrics_endpoint(http_client):
    response = await http_client.get("/metrics")
    assert response.status_code == 200
    assert b"buc_mcp" in response.content
