import pytest
from fastmcp import Client

from src.server import mcp


@pytest.mark.anyio
async def test_prompts_listed():
    async with Client(mcp) as client:
        prompts = await client.list_prompts()
    names = [p.name for p in prompts]
    assert "code_review" in names


@pytest.mark.anyio
async def test_code_review_prompt_default():
    async with Client(mcp) as client:
        result = await client.get_prompt("code_review")
    assert "python" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_code_review_prompt_language():
    async with Client(mcp) as client:
        result = await client.get_prompt("code_review", {"language": "typescript"})
    assert "typescript" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_skills_discovered():
    async with Client(mcp) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert any("traintimes" in uri for uri in uris)


@pytest.mark.anyio
async def test_traintimes_skill_readable():
    async with Client(mcp) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    traintimes_uri = next(uri for uri in uris if "traintimes" in uri)
    async with Client(mcp) as client:
        content = await client.read_resource(traintimes_uri)
    assert content
