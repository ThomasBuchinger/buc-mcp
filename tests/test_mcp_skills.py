import pytest
from fastmcp import Client

from src.server import syncSkill


@pytest.mark.anyio
async def test_resources_listed():
    async with Client(syncSkill) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    assert any("mattpocock-tdd" in uri for uri in uris)
    assert any("kubernetes-yaml" in uri for uri in uris)


@pytest.mark.anyio
async def test_resource_readable():
    async with Client(syncSkill) as client:
        resources = await client.list_resources()
    uris = [str(r.uri) for r in resources]
    mattpocock_uri = next(uri for uri in uris if "mattpocock-tdd" in uri)
    async with Client(syncSkill) as client:
        content = await client.read_resource(mattpocock_uri)
    assert content
