"""
Unit tests for app.upt_engine.formulas.UPTMath
"""
import math
import pytest
from app.upt_engine.formulas import UPTMath


# ── calculate_collapse_probability ───────────────────────────────────────────
class TestCalculateCollapseProbability:

    def test_nominal_values(self):
        """Standard mid-range inputs should return their product."""
        result = UPTMath.calculate_collapse_probability(0.5, 0.5, 0.5)
        assert result == pytest.approx(0.125, rel=1e-6)

    def test_zero_anomaly_gives_zero(self):
        result = UPTMath.calculate_collapse_probability(0.0, 0.8, 0.9)
        assert result == 0.0

    def test_zero_energy_gives_zero(self):
        result = UPTMath.calculate_collapse_probability(0.8, 0.0, 0.9)
        assert result == 0.0

    def test_zero_vulnerability_gives_zero(self):
        result = UPTMath.calculate_collapse_probability(0.8, 0.8, 0.0)
        assert result == 0.0

    def test_max_inputs_give_one(self):
        result = UPTMath.calculate_collapse_probability(1.0, 1.0, 1.0)
        assert result == pytest.approx(1.0)

    def test_clamps_above_one(self):
        """Values > 1.0 must be clamped to 1.0 before multiplication."""
        result = UPTMath.calculate_collapse_probability(2.0, 2.0, 2.0)
        assert result == pytest.approx(1.0)

    def test_clamps_below_zero(self):
        """Negative inputs must be clamped to 0.0."""
        result = UPTMath.calculate_collapse_probability(-0.5, 0.5, 0.5)
        assert result == 0.0

    def test_asymmetric_mix(self):
        result = UPTMath.calculate_collapse_probability(0.3, 0.6, 0.8)
        assert result == pytest.approx(0.3 * 0.6 * 0.8, rel=1e-6)


# ── calculate_resonance ───────────────────────────────────────────────────────
class TestCalculateResonance:

    def test_empty_returns_zero(self):
        assert UPTMath.calculate_resonance([]) == 0.0

    def test_single_sensor(self):
        sensors = [{"anomaly_score": 0.5, "energy_level": 0.4}]
        expected = (0.5 * 0.4) / 1
        assert UPTMath.calculate_resonance(sensors) == pytest.approx(expected)

    def test_multi_sensor_average(self):
        sensors = [
            {"anomaly_score": 0.6, "energy_level": 0.8},
            {"anomaly_score": 0.4, "energy_level": 0.2},
        ]
        total_a = 0.6 + 0.4   # 1.0
        total_e = 0.8 + 0.2   # 1.0
        expected = (total_a * total_e) / 2
        assert UPTMath.calculate_resonance(sensors) == pytest.approx(expected)

    def test_missing_keys_default_zero(self):
        """Sensors without energy/anomaly keys should default to 0."""
        sensors = [{}]
        result = UPTMath.calculate_resonance(sensors)
        assert result == pytest.approx(0.0)


# ── calculate_stability ───────────────────────────────────────────────────────
class TestCalculateStability:

    def test_nominal(self):
        result = UPTMath.calculate_stability(0.5, 0.1, 0.2)
        expected = 0.5 / (1.0 + 0.1 + 0.2)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_zero_resonance(self):
        result = UPTMath.calculate_stability(0.0, 0.1, 0.2)
        assert result == pytest.approx(0.0)

    def test_zero_denominator_safety(self):
        """denominator = 1 + 0 + 0 = 1; should never divide by zero."""
        result = UPTMath.calculate_stability(1.0, 0.0, 0.0)
        assert result == pytest.approx(1.0)


# ── calculate_geomagnetic_coupling ───────────────────────────────────────────
class TestCalculateGeomagneticCoupling:

    K = 0.15  # Must match UPTMath.K_COUPLING

    def test_b_class_flare(self):
        energy = 0.1  # B-class
        expected = min((energy ** 1.5) * self.K, 2.0)
        result = UPTMath.calculate_geomagnetic_coupling(energy)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_c_class_flare(self):
        energy = 0.3
        expected = min((energy ** 1.5) * self.K, 2.0)
        result = UPTMath.calculate_geomagnetic_coupling(energy)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_m_class_flare(self):
        energy = 0.6
        expected = min((energy ** 1.5) * self.K, 2.0)
        result = UPTMath.calculate_geomagnetic_coupling(energy)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_x_class_flare_max_energy(self):
        energy = 1.0  # X-class
        expected = min((1.0 ** 1.5) * self.K, 2.0)
        result = UPTMath.calculate_geomagnetic_coupling(energy)
        assert result == pytest.approx(expected, rel=1e-5)

    def test_capped_at_two(self):
        """Impact must never exceed 2.0 regardless of input."""
        result = UPTMath.calculate_geomagnetic_coupling(10.0, earth_field_strength=0.001)
        assert result <= 2.0

    def test_weak_field_amplifies_impact(self):
        """Weaker Earth field → stronger coupling."""
        normal = UPTMath.calculate_geomagnetic_coupling(0.5, earth_field_strength=1.0)
        weak   = UPTMath.calculate_geomagnetic_coupling(0.5, earth_field_strength=0.5)
        assert weak > normal

    def test_zero_energy_gives_zero(self):
        result = UPTMath.calculate_geomagnetic_coupling(0.0)
        assert result == pytest.approx(0.0)
