"""
性能测试专用配置和fixtures
"""
import pytest
from httpx import AsyncClient, ASGITransport
from src.api.main import app


@pytest.fixture
async def performance_client():
    """性能测试专用AsyncClient（不使用mock）"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
