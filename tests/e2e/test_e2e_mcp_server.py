import pytest

from e2e_actions import *
from e2e_actions import read_prompt, read_resource

@pytest.mark.anyio
async def test_e2e_proxy_reports_not_configured_without_api_key(e2e_http_client, monkeypatch):
    """Without CONTEXT7_API_KEY the proxy is effectively absent"""
    start_mcpserver_for_e2e_tests()
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    response = await e2e_http_client.get("/health/context7/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "not configured"


@pytest.mark.anyio
async def test_e2e_proxy_health_endpoint_exists(e2e_http_client, monkeypatch):
    """The dedicated proxy health endpoint exists regardless of key state (story 5)."""
    start_mcpserver_for_e2e_tests()
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    response = await e2e_http_client.get("/health/context7/ready")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_e2e_parent_readiness_does_not_check_proxy(e2e_http_client, monkeypatch):
    """Parent /health/ready must stay ready even when the proxy is not configured (story 6)."""
    start_mcpserver_for_e2e_tests()
    monkeypatch.delenv("CONTEXT7_API_KEY", raising=False)
    response = await e2e_http_client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


@pytest.mark.anyio
async def test_e2e_proxy_metrics_exposed(e2e_http_client):
    """Prometheus exposes proxy request counters and histograms (story 8)."""
    start_mcpserver_for_e2e_tests()
    # any HTTP request traverses the ProxyMetricsMiddleware and records a sample
    await e2e_http_client.get("/health/live")
    response = await e2e_http_client.get("/metrics")
    assert response.status_code == 200
    assert "buc_mcp_proxy_requests_total" in response.text
    assert "buc_mcp_proxy_request_duration_seconds" in response.text
    assert "buc_mcp_proxy_errors_total" in response.text


@pytest.mark.anyio
async def test_e2e_liveness_probe_returns_200_when_alive(e2e_http_client):
    start_mcpserver_for_e2e_tests()
    response = await e2e_http_client.get("/health/live")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_e2e_readiness_probe_returns_200_when_providers_functional(e2e_http_client):
    start_mcpserver_for_e2e_tests()
    response = await e2e_http_client.get("/health/ready")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_e2e_metrics_endpoint_exposes_prometheus_metrics(e2e_http_client):
    start_mcpserver_for_e2e_tests()
    response = await e2e_http_client.get("/metrics")
    assert response.status_code == 200
    assert "buc_mcp_" in response.text

