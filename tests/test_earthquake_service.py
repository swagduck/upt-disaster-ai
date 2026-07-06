"""
Unit tests for upt_guardian.deep_core.DeepGuardian._extract_features
and app.services.earthquake_service.DisasterService (mocked HTTP calls).
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx


# ── _extract_features (DeepGuardian) ─────────────────────────────────────────
class TestExtractFeatures:
    """Test the feature extraction helper without instantiating the full model."""

    @pytest.fixture(autouse=True)
    def guardian(self):
        # Prevent DB calls and TF model build during test collection
        with patch("upt_guardian.deep_core.DeepGuardian.train"):
            from upt_guardian.deep_core import DeepGuardian
            self.brain = DeepGuardian.__new__(DeepGuardian)
            self.brain.look_back = 5

    def test_empty_sensors_returns_zeros(self):
        result = self.brain._extract_features([])
        assert result == [0, 0, 0, 0, 0]

    def test_vector_length_is_five(self, sample_sensors):
        result = self.brain._extract_features(sample_sensors)
        assert len(result) == 5

    def test_cosmic_energy_from_solar_flare(self, sample_sensors):
        """The 5th feature must reflect the highest SOLAR_FLARE energy_level."""
        result = self.brain._extract_features(sample_sensors)
        # sample_sensors contains a SOLAR_FLARE with energy_level=1.0
        assert result[4] == pytest.approx(1.0)

    def test_no_solar_flare_gives_zero_cosmic(self):
        sensors = [
            {"type": "EARTHQUAKE", "energy_level": 0.5, "anomaly_score": 0.4, "raw_val": 5.0}
        ]
        result = self.brain._extract_features(sensors)
        assert result[4] == pytest.approx(0.0)

    def test_avg_energy_calculation(self, sample_sensors):
        """avg_energy = mean of energy_level across all sensors."""
        import numpy as np
        expected_avg = float(
            np.mean([s["energy_level"] for s in sample_sensors])
        )
        result = self.brain._extract_features(sample_sensors)
        assert result[0] == pytest.approx(expected_avg, rel=1e-5)

    def test_max_mag_normalised(self, sample_sensors):
        """max raw_val should be divided by 10.0."""
        max_raw = max(s["raw_val"] for s in sample_sensors)
        result = self.brain._extract_features(sample_sensors)
        assert result[2] == pytest.approx(max_raw / 10.0, rel=1e-5)


# ── DisasterService.fetch_all_realtime (mocked) ───────────────────────────────
class TestDisasterServiceFetch:
    """Verify fetch_all_realtime processes API responses without hitting the network."""

    @pytest.fixture
    def usgs_geojson(self):
        return {
            "features": [
                {
                    "properties": {"mag": 6.5, "place": "Near Tokyo", "sig": 800},
                    "geometry": {"coordinates": [139.69, 35.68, 10.0]},
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_processes_usgs_earthquake(self, usgs_geojson):
        """A magnitude 6.5 event must be added to sensor list and trigger reactor shock."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = usgs_geojson

        empty_resp = MagicMock(spec=httpx.Response)
        empty_resp.status_code = 200
        empty_resp.json.return_value = {"events": [], "features": []}  # EONET and GDACS

        solar_resp = MagicMock(spec=httpx.Response)
        solar_resp.status_code = 200
        solar_resp.json.return_value = []  # DONKI

        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.earthquake_service.upt_reactor") as mock_reactor, \
             patch("app.services.earthquake_service.guardian_brain"), \
             patch("app.core.database.Database.get_collection", return_value=None):

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[mock_resp, empty_resp, solar_resp, empty_resp]
            )
            mock_client_cls.return_value = mock_client

            from app.services.earthquake_service import DisasterService
            DisasterService.alerted_events.clear()
            result = await DisasterService.fetch_all_realtime()

        # Must have collected the earthquake sensor
        assert any(s["type"] == "EARTHQUAKE" for s in result)
        # Must have triggered reactor stress for mag >= 6.0
        mock_reactor.update_external_stress.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_low_magnitude_events(self):
        """Earthquakes below M1.0 must be filtered out."""
        usgs_data = {
            "features": [
                {
                    "properties": {"mag": 0.8, "place": "Micro Quake", "sig": 10},
                    "geometry": {"coordinates": [100.0, 5.0, 5.0]},
                }
            ]
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = usgs_data

        empty_resp = MagicMock(spec=httpx.Response)
        empty_resp.status_code = 200
        empty_resp.json.return_value = {"events": [], "features": []}

        solar_resp = MagicMock(spec=httpx.Response)
        solar_resp.status_code = 200
        solar_resp.json.return_value = []

        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.earthquake_service.upt_reactor"), \
             patch("app.services.earthquake_service.guardian_brain"), \
             patch("app.core.database.Database.get_collection", return_value=None):

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[mock_resp, empty_resp, solar_resp, empty_resp]
            )
            mock_client_cls.return_value = mock_client

            from app.services.earthquake_service import DisasterService
            DisasterService.alerted_events.clear()
            result = await DisasterService.fetch_all_realtime()

        assert result == []

    @pytest.mark.asyncio
    async def test_no_telegram_when_bot_not_configured(self, usgs_geojson):
        """Alerts must silently no-op when Telegram is not configured."""
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = usgs_geojson

        empty_resp = MagicMock(spec=httpx.Response)
        empty_resp.status_code = 200
        empty_resp.json.return_value = {"events": []}

        solar_resp = MagicMock(spec=httpx.Response)
        solar_resp.status_code = 200
        solar_resp.json.return_value = []

        with patch("httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.earthquake_service.upt_reactor"), \
             patch("app.services.earthquake_service.guardian_brain"), \
             patch("app.core.database.Database.get_collection", return_value=None):

            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(
                side_effect=[mock_resp, empty_resp, solar_resp]
            )
            mock_client_cls.return_value = mock_client

            from app.services.earthquake_service import DisasterService
            original_bot = DisasterService.bot
            DisasterService.bot = None
            DisasterService.alerted_events.clear()

            # Should not raise even though a M6.5 triggers an alert
            await DisasterService.fetch_all_realtime()

            DisasterService.bot = original_bot
