"""
API endpoint tests for UPT Disaster AI.

Tests the FastAPI routes using httpx.AsyncClient (the modern approach)
without requiring a live MongoDB or external API connection.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

# Patch heavy dependencies BEFORE importing app
# This prevents TensorFlow init, MongoDB connection, etc. during test collection
with patch("app.upt_engine.deep_core.Database"):
    with patch("app.upt_engine.deep_core.tf"):
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
    assert body["model_type"] == "LSTM (TensorFlow/Keras)"
    assert "buffer_size" in body


# ═══════════════════════════════════════════════════════════════════════════════
# Protected endpoints — test without API key (should work in dev mode)
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.anyio
async def test_scram_dev_mode(client):
    """POST /api/v1/reactor/scram should succeed without API key in dev mode."""
    # In dev mode (API_SECRET_KEY=None), auth is skipped
    resp = await client.post("/api/v1/reactor/scram")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SCRAM_EXECUTED"


@pytest.mark.anyio
async def test_inject_event_dev_mode(client):
    """POST /api/v1/reactor/inject-event should accept magnitude param."""
    resp = await client.post("/api/v1/reactor/inject-event?magnitude=5.0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "SHOCK_RECEIVED"
    assert body["damage"] == 0.0  # magnitude < 6.0 → no shock


@pytest.mark.anyio
async def test_inject_event_major(client):
    """A magnitude > 6.0 should produce a shock."""
    resp = await client.post("/api/v1/reactor/inject-event?magnitude=7.0")
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

@pytest.mark.anyio
async def test_predict_no_sensors(client):
    """POST /api/v1/predict/predict with empty sensors → error."""
    resp = await client.post("/api/v1/predict/predict", json={
        "region_name": "Test Region",
        "sensors": [],
        "geo_vulnerability": 0.5,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body


@pytest.mark.anyio
async def test_predict_with_sensors(client):
    """POST /api/v1/predict/predict with valid data → prediction result."""
    resp = await client.post("/api/v1/predict/predict", json={
        "region_name": "Tokyo",
        "sensors": [
            {"station_id": "S1", "energy_level": 0.8, "anomaly_score": 0.6},
            {"station_id": "S2", "energy_level": 0.3, "anomaly_score": 0.2},
        ],
        "geo_vulnerability": 0.7,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert "probability_index" in body
    assert "alert_level" in body
    assert body["region"] == "Tokyo"


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
