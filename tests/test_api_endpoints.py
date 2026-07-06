"""
API endpoint tests for UPT Disaster AI.

Tests the FastAPI routes using httpx.AsyncClient (the modern approach)
without requiring a live MongoDB or external API connection.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

with patch("app.upt_engine.deep_core.Database"):
    from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client — no real server needed."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ═══════════════════════════════════════════════════════════════════════════════
# GET endpoints (no auth required)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_get_index(client):
    """The root URL should serve the main HTML page."""
    resp = await client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.anyio
async def test_get_dashboard(client):
    """The /dashboard URL should serve the dashboard HTML page."""
    resp = await client.get("/dashboard")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


@pytest.mark.anyio
async def test_get_disasters_live(client):
    """GET /api/v1/disasters/live should return cached sensor data."""
    resp = await client.get("/api/v1/disasters/live")
    assert resp.status_code == 200
    body = resp.json()
    assert "source" in body
    assert "count" in body
    assert "data" in body


@pytest.mark.anyio
async def test_get_stats_summary(client):
    """GET /api/v1/stats/summary should return summary dict."""
    resp = await client.get("/api/v1/stats/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "type_counts" in body


@pytest.mark.anyio
async def test_get_ai_status(client):
    """GET /api/v1/predict/status should return AI brain status."""
    resp = await client.get("/api/v1/predict/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert body["model_type"] == "Deep Learning LSTM (TensorFlow/Keras)"


# ═══════════════════════════════════════════════════════════════════════════════
# Protected endpoints — test without API key (should work in dev mode)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_scram_with_auth(client):
    """POST /api/v1/reactor/scram should succeed with correct API key."""
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.API_SECRET_KEY = "test-key"
        resp = await client.post("/api/v1/reactor/scram", headers={"X-API-Key": "test-key"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "SCRAM_EXECUTED"

@pytest.mark.anyio
async def test_inject_event_major(client):
    """A magnitude > 6.0 should produce a shock."""
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.API_SECRET_KEY = "test-key"
        resp = await client.post("/api/v1/reactor/inject-event?magnitude=7.0", headers={"X-API-Key": "test-key"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["damage"] == 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# Protected endpoints — test WITH wrong API key (when configured)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_scram_wrong_api_key(client):
    """If API_SECRET_KEY is set, wrong key should be rejected."""
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.API_SECRET_KEY = "correct-key"
        resp = await client.post(
            "/api/v1/reactor/scram",
            headers={"X-API-Key": "wrong-key"},
        )
        assert resp.status_code == 403


@pytest.mark.anyio
async def test_scram_correct_api_key(client):
    """If API_SECRET_KEY is set, correct key should be accepted."""
    with patch("app.core.security.settings") as mock_settings:
        mock_settings.API_SECRET_KEY = "correct-key"
        resp = await client.post(
            "/api/v1/reactor/scram",
            headers={"X-API-Key": "correct-key"},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# Formula-based prediction endpoint
# ═══════════════════════════════════════════════════════════════════════════════

# Deleted endpoints tests removed


# ═══════════════════════════════════════════════════════════════════════════════
# Stats endpoint
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_get_stats_trend(client):
    """GET /api/v1/stats/trend should return time-series points."""
    resp = await client.get("/api/v1/stats/trend?hours=24")
    assert resp.status_code == 200
    body = resp.json()
    assert "points" in body
