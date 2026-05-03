import pytest
from fastmcp import Client

from src.server import kubernetes


@pytest.mark.anyio
async def test_prompts_listed():
    async with Client(kubernetes) as client:
        prompts = await client.list_prompts()
    names = [p.name for p in prompts]
    assert "kubernetes_yaml" in names


@pytest.mark.anyio
async def test_kubernetes_yaml_skill_is_accessible_as_popmpt():
    async with Client(kubernetes) as client:
        result = await client.get_prompt("kubernetes_yaml")
    assert "kubernetes" in result.messages[0].content.text.lower()

@pytest.mark.anyio
async def test_prompt_is_extendable():
    async with Client(kubernetes) as client:
        result = await client.get_prompt(
            "kubernetes_yaml",
            {
                "prompt": "the user can add additional stuff to the prompt, like the word foobar"
            },
        )
    assert "foobar" in result.messages[0].content.text.lower()


@pytest.mark.anyio
async def test_skills_discovered():
    async with Client(kubernetes) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    print(uris)
    assert any("kubernetes-yaml" in uri for uri in uris)


@pytest.mark.anyio
async def test_kubernetesyaml_skill_readable():
    async with Client(kubernetes) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    kubernetesyaml_uri = next(uri for uri in uris if "kubernetes-yaml" in uri)
    async with Client(kubernetes) as client:
        content = await client.read_resource(kubernetesyaml_uri)
    assert content
