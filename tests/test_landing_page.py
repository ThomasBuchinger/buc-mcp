import pytest

from src.server import app


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    return TestClient(app)


def test_landing_page_root(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "htmx.org" in html
    assert "BUC-MCP" in html
    assert "hx-get=\"/sections/sync\"" in html
    assert "hx-get=\"/sections/servers\"" in html
    assert "hx-get=\"/sections/skills\"" in html
    assert "hx-get=\"/sections/configs\"" in html


def test_section_sync(client):
    response = client.get("/sections/sync")
    assert response.status_code == 200
    assert "curl" in response.text
    assert "sync.sh" in response.text
    assert "copy-btn" in response.text or "clipboard" in response.text


def test_section_servers(client):
    response = client.get("/sections/servers")
    assert response.status_code == 200
    assert "/mcp" in response.text
    assert "Mounted" in response.text


def test_section_skills(client):
    response = client.get("/sections/skills")
    assert response.status_code == 200
    assert "hx-get" in response.text
    # should contain at least one category
    assert "skills" in response.text or "coding" in response.text


def test_section_skills_category(client):
    response = client.get("/sections/skills/coding-passive")
    assert response.status_code == 200
    assert "skill-link" in response.text


def test_section_skill_view(client):
    response = client.get("/sections/skill/kubernetes-yaml")
    assert response.status_code == 200
    assert "skill-content" in response.text


def test_section_skill_view_not_found(client):
    response = client.get("/sections/skill/nonexistent-skill-xyz")
    assert response.status_code == 404


def test_section_configs(client):
    response = client.get("/sections/configs")
    assert response.status_code == 200
    # should list servers from mcp.json
    assert "config-name" in response.text


def test_sections_invalid(client):
    response = client.get("/sections/nonexistent")
    assert response.status_code == 405 or response.status_code == 404
