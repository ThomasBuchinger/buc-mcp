import pytest

from src.server import app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_mcps_json_default_agent_is_opencode(client):
    response = client.get("/mcps.json")
    assert response.status_code == 200
    data = response.json()
    assert "mcp" in data
    assert "mcpServers" not in data


def test_mcps_json_opencode_format(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    assert "mcp" in data
    assert "mcpServers" not in data
    # remote servers stay remote, stdio stays stdio
    exa = data["mcp"]["exa"]
    assert exa["type"] == "remote"
    browser_use = data["mcp"]["browser-use"]
    assert browser_use["type"] == "stdio"


def test_mcps_json_claude_format(client):
    response = client.get("/mcps.json?agent=claude")
    assert response.status_code == 200
    data = response.json()
    assert "mcpServers" in data
    assert "mcp" not in data
    # remote -> http, stdio stays stdio
    exa = data["mcpServers"]["exa"]
    assert exa["type"] == "http"
    browser_use = data["mcpServers"]["browser-use"]
    assert browser_use["type"] == "stdio"


def test_mcps_json_preserves_url(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    assert data["mcp"]["exa"]["url"] == "http://10.0.0.190:8080/exa/mcp"


def test_mcps_json_skips_schema(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    assert "$schema" not in data
    for server in data.get("mcp", data.get("mcpServers", {}).values()):
        assert "$schema" not in server


def test_mcps_json_skips_enabled(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    for server in data.get("mcp", data.get("mcpServers", {}).values()):
        assert "enabled" not in server


def test_mcps_json_preserves_headers(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    context7 = data["mcp"].get("context7", {})
    assert "headers" in context7
    assert context7["headers"]["CONTEXT7_API_KEY"] == "{env:CONTEXT7_API_KEY}"


def test_mcps_json_preserves_env(client):
    response = client.get("/mcps.json?agent=opencode")
    assert response.status_code == 200
    data = response.json()
    browser_use = data["mcp"].get("browser-use", {})
    assert "env" in browser_use
    assert browser_use["env"]["OPENAI_API_KEY"] == "aaa"



