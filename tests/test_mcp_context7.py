import os
import pytest


@pytest.mark.anyio
async def test_context7_health_not_configured_without_api_key(http_client, monkeypatch):
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    response = await http_client.get("/health/context7/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not configured"


@pytest.mark.anyio
async def test_context7_health_configured_with_api_key(http_client):
    response = await http_client.get("/health/context7/ready")
    assert response.status_code == 200
