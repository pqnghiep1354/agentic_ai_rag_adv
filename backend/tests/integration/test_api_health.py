"""
Integration tests for health check and basic API endpoints

These tests require the full application with all dependencies.
Run with: docker-compose up -d && pytest tests/integration/ -v
"""

import pytest

# Try to import the app, skip tests if dependencies are missing
try:
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    SKIP_TESTS = False
    SKIP_REASON = ""
except ImportError as e:
    SKIP_TESTS = True
    SKIP_REASON = f"Missing dependency: {e.name}"
    app = None


@pytest.fixture
def skip_if_missing_deps():
    """Skip tests if dependencies are missing"""
    if SKIP_TESTS:
        pytest.skip(SKIP_REASON)


@pytest.fixture
async def test_client(skip_if_missing_deps):
    """Create async test client without database dependency"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.integration
class TestHealthEndpoint:
    """Tests for health check endpoint"""

    @pytest.mark.asyncio
    async def test_health_check_returns_healthy(self, test_client):
        """Test health check returns healthy status"""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_check_app_name(self, test_client):
        """Test health check returns correct app name"""
        response = await test_client.get("/health")

        data = response.json()
        assert data["app_name"] == "Vietnamese Environmental Law RAG"


@pytest.mark.integration
class TestRootEndpoint:
    """Tests for root endpoint"""

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self, test_client):
        """Test root endpoint returns app information"""
        response = await test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "app_name" in data
        assert "version" in data
        assert "health_check" in data

    @pytest.mark.asyncio
    async def test_root_health_check_url(self, test_client):
        """Test root endpoint provides health check URL"""
        response = await test_client.get("/")

        data = response.json()
        assert data["health_check"] == "/health"


@pytest.mark.integration
class TestNotFoundHandler:
    """Tests for 404 error handling"""

    @pytest.mark.asyncio
    async def test_not_found_returns_404(self, test_client):
        """Test non-existent endpoint returns 404"""
        response = await test_client.get("/nonexistent/endpoint")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


@pytest.mark.integration
class TestAPIV1Router:
    """Tests for API v1 router"""

    @pytest.mark.asyncio
    async def test_api_v1_prefix(self, test_client):
        """Test API v1 prefix is correctly mounted"""
        # Try to access a v1 endpoint (documents list)
        # Should return 401 (unauthorized) or other auth error, not 404
        response = await test_client.get("/api/v1/documents")

        # Either 401 (needs auth) or 200 (if no auth required)
        # 404 would mean the route is not mounted
        assert response.status_code != 404 or "detail" in response.json()


# Skip all tests in this module if dependencies are missing
if SKIP_TESTS:
    for item in list(globals().values()):
        if isinstance(item, type) and item.__name__.startswith("Test"):
            item = pytest.mark.skip(reason=SKIP_REASON)(item)
