"""E2E test fixtures."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def e2e_http_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://e2e"
    ) as client:
        yield client
