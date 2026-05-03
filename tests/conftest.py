import pytest
from httpx import ASGITransport, AsyncClient

from src.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def http_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
