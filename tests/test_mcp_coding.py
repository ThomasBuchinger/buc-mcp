import pytest
from fastmcp import Client

from src.server import coding



@pytest.mark.anyio
async def test_prompts_listed():
    async with Client(coding) as client:
        prompts = await client.list_prompts()
    names = [p.name for p in prompts]
    assert "prd_create" in names
    assert "prd_start" in names
    assert "prd_next" in names
    assert "prd_update_decisions" in names


@pytest.mark.anyio
async def test_prompts_extendable():
    async with Client(coding) as client:
        result = await client.get_prompt(
            "prd_create",
            {
                "prompt": "the user can add additional stuff to the prompt, like the word foobar"
            },
        )
    assert "foobar" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_skills_discovered():
    async with Client(coding) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert any("frontend-design" in uri for uri in uris)


@pytest.mark.anyio
async def test_traintimes_skill_readable():
    async with Client(coding) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    traintimes_uri = next(uri for uri in uris if "frontend-design" in uri)
    async with Client(coding) as client:
        content = await client.read_resource(traintimes_uri)
    assert content
