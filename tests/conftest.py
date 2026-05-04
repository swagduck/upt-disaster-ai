"""
Shared pytest fixtures for UPT Disaster AI test suite.
"""
import pytest
from unittest.mock import MagicMock, patch


# ── Reactor Fixture ───────────────────────────────────────────────────────────
@pytest.fixture
def fresh_reactor():
    """Return a brand-new UPTReactorCore instance (not the running singleton)."""
    # Patch asyncio.create_task so start_reactor() doesn't need an event loop
    with patch("asyncio.create_task"):
        from app.upt_engine.reactor_core import UPTReactorCore
        reactor = UPTReactorCore()
    return reactor


# ── Sample Sensor Data Fixtures ───────────────────────────────────────────────
@pytest.fixture
def sample_sensors():
    """A realistic list of sensor dicts resembling DisasterService output."""
    return [
        {
            "type": "EARTHQUAKE",
            "place": "10km NW of Test City",
            "lat": 36.2, "lon": 138.2,
            "energy_level": 0.78,
            "anomaly_score": 0.65,
            "raw_val": 7.0,
        },
        {
            "type": "VOLCANO",
            "place": "Kilauea, Hawaii",
            "lat": 19.4, "lon": -155.3,
            "energy_level": 0.95,
            "anomaly_score": 0.80,
            "raw_val": 5.0,
        },
        {
            "type": "SOLAR_FLARE",
            "place": "Sunspot 3590 (X1.2)",
            "lat": 90.0, "lon": 0.0,
            "energy_level": 1.0,
            "anomaly_score": 0.99,
            "raw_val": 10.0,
        },
    ]


@pytest.fixture
def empty_sensors():
    return []
