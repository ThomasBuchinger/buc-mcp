"""E2E test abstraction layer.

This module maps low-level API actions to human-readable function names so
E2E tests read like scenarios. Tests must NOT reach into internals directly;
they go through the helpers defined here.

Convention:
  - Action functions use PascalCase verbs (Start_, Get_, Fetch_, Call_...)
  - Pure mapping/translation helpers use snake_case (map_..., extract_...)
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
from fastmcp import Client
from httpx import ASGITransport, AsyncClient

from src.server import app


def _reset_env_for_clean_server() -> None:
    """Ensure the server boots in a clean, deterministic state for E2E runs.

    The Context7 proxy is only mounted when CONTEXT7_API_KEY is set. For the
    basic E2E suite we boot without it so the proxy endpoint is absent and
    /health/context7/ready reports "not configured".
    """
    os.environ.pop("CONTEXT7_API_KEY", None)


@pytest.fixture
async def e2e_http_client() -> AsyncIterator[AsyncClient]:
    """A dedicated HTTP client wired to the running buc-mcp ASGI app.

    Equivalent to Get_E2E_MCP_Client() for HTTP-level actions (health, metrics).
    """
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://e2e"
    ) as client:
        yield client


def start_mcpserver_for_e2e_tests() -> None:
    """Boot the buc-mcp server with Dummy Backend implementations.

    This is the entry point every E2E scenario begins with. It guarantees a
    clean, deterministic server state. Currently it boots the real ASGI app
    with no upstream Context7 API key configured (proxy endpoint absent).

    NOTE: Once the coder provides Dummy Backends (e.g. a dummy Context7
    upstream), this function is the single place to wire them in.
    """
    _reset_env_for_clean_server()


def get_e2e_httpclient() -> AsyncClient:
    """Get a dedicated HTTP test client for HTTP-level actions.

    Returned as a bare AsyncClient for use inside scenarios; tests typically
    use the `e2e_http_client` fixture instead. Provided for parity with the
    MCP client helper.
    """
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://e2e")


def get_e2emcpclient(server_name: str = "buc-coding") -> Client:
    """Get a dedicated MCP client connected to a named buc-mcp sub-server.

    Args:
        server_name: one of "buc-coding", "buc-kubernetes", "buc-skills",
            "buc-personal", or "buc-context7".
    """
    from src.mcp import (
        coding,
        context7,
        kubernetes,
        mcp_personal,
        syncSkill,
    )

    servers = {
        "buc-coding": coding,
        "buc-kubernetes": kubernetes,
        "buc-skills": syncSkill,
        "buc-personal": mcp_personal,
        "buc-context7": context7,
    }
    if server_name not in servers:
        raise ValueError(
            f"Unknown buc-mcp server: {server_name!r}. "
            f"Known: {sorted(servers)}"
        )
    return Client(servers[server_name])


async def fetch_prompts(client: Client):
    """List all prompts exposed by the connected MCP server."""
    async with client:
        return await client.list_prompts()


async def fetch_resources(client: Client):
    """List all resources (skills) exposed by the connected MCP server."""
    async with client:
        return await client.list_resources()


async def fetch_tools(client: Client):
    """List all tools exposed by the connected MCP server."""
    async with client:
        return await client.list_tools()


async def read_prompt(client: Client, name: str):
    """Read a specific prompt by name."""
    async with client:
        return await client.get_prompt(name)


async def read_resource(client: Client, uri: str):
    """Read a specific resource by URI."""
    async with client:
        return await client.read_resource(uri)


async def call_tool(client: Client, name: str, arguments: dict | None = None):
    """Call a tool by name with the given arguments."""
    async with client:
        return await client.call_tool(name, arguments or {})


# --- mapping helpers: translate raw results into readable names ---


def map_prompts_result_to_names(prompts) -> list[str]:
    return [p.name for p in prompts]


def map_resources_to_uris(resources) -> list[str]:
    return [str(r.uri) for r in resources]


def map_tools_result_to_names(tools) -> list[str]:
    return [t.name for t in tools]
