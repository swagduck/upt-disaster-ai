"""
Unit tests for upt_guardian.reactor_core.UPTReactorCore
"""
import pytest
from unittest.mock import patch


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_reactor():
    """Return a fresh UPTReactorCore without touching the running singleton."""
    with patch("threading.Thread"):
        from upt_guardian.reactor_core import UPTReactorCore
        return UPTReactorCore()


# ── Initial State ─────────────────────────────────────────────────────────────
class TestInitialState:

    def test_starts_offline(self):
        r = make_reactor()
        assert r.status_code == "OFFLINE"
        assert not r.is_running

    def test_initial_temp_is_ambient(self):
        r = make_reactor()
        assert r.core_temp == pytest.approx(300.0)

    def test_initial_flux_is_zero(self):
        r = make_reactor()
        assert r.neutron_flux == 0.0

    def test_initial_geomagnetic_residual_zero(self):
        r = make_reactor()
        assert r.geomagnetic_residual == 0.0


# ── start_reactor ─────────────────────────────────────────────────────────────
class TestStartReactor:

    def test_sets_running_flag(self):
        r = make_reactor()
        with patch("threading.Thread") as mock_thread:
            r.start_reactor()
        assert r.is_running

    def test_sets_startup_status(self):
        r = make_reactor()
        with patch("threading.Thread") as mock_thread:
            r.start_reactor()
        assert r.status_code == "STARTUP"

    def test_idempotent_double_start(self):
        """Calling start_reactor twice must not reset state."""
        r = make_reactor()
        with patch("threading.Thread") as mock_thread:
            r.start_reactor()
            r.start_reactor()
        # Thread start should only have been called once
        assert mock_thread.call_count == 1


# ── trigger_phase_detuning ────────────────────────────────────────────────────
class TestTriggerPhaseDetuning:

    def test_sets_scram_status(self):
        r = make_reactor()
        r.status_code = "NOMINAL"
        r.trigger_phase_detuning()
        assert r.status_code == "SCRAM"

    def test_maxes_control_rods(self):
        r = make_reactor()
        r.control_rods = 50.0
        r.trigger_phase_detuning()
        assert r.control_rods == 100.0

    def test_resets_plasma(self):
        r = make_reactor()
        r.r_plasma = 0.9
        r.trigger_phase_detuning()
        assert r.r_plasma == 0.0

    def test_noop_when_already_scram(self):
        r = make_reactor()
        r.status_code = "SCRAM"
        r.control_rods = 40.0   # deliberately wrong
        r.trigger_phase_detuning()
        assert r.control_rods == 40.0   # must NOT change


# ── inject_cosmic_interference ────────────────────────────────────────────────
class TestInjectCosmicInterference:

    def test_accumulates_residual(self):
        r = make_reactor()
        r.inject_cosmic_interference(0.5)
        assert r.geomagnetic_residual == pytest.approx(0.5)

    def test_accumulates_multiple_injections(self):
        r = make_reactor()
        r.inject_cosmic_interference(0.3)
        r.inject_cosmic_interference(0.4)
        assert r.geomagnetic_residual == pytest.approx(0.7)

    def test_ignores_weak_signal(self):
        """Signals ≤ 0.05 must be discarded (below detection threshold)."""
        r = make_reactor()
        r.inject_cosmic_interference(0.04)
        assert r.geomagnetic_residual == 0.0

    def test_boundary_signal_accepted(self):
        """Signal just above threshold (0.06) must be accepted."""
        r = make_reactor()
        r.inject_cosmic_interference(0.06)
        assert r.geomagnetic_residual == pytest.approx(0.06)


# ── update_external_stress ────────────────────────────────────────────────────
class TestUpdateExternalStress:

    def test_large_stress_increases_noise(self):
        r = make_reactor()
        initial_noise = r.phase_noise
        r.update_external_stress(1.0)
        assert r.phase_noise > initial_noise

    def test_noise_proportional_to_stress(self):
        r = make_reactor()
        r.update_external_stress(1.0)
        noise_1 = r.phase_noise

        r2 = make_reactor()
        r2.update_external_stress(0.8)
        noise_2 = r2.phase_noise

        assert noise_1 > noise_2

    def test_weak_stress_ignored(self):
        """Stress ≤ 0.5 must not affect phase_noise."""
        r = make_reactor()
        r.update_external_stress(0.5)
        assert r.phase_noise == 0.0


# ── get_status ────────────────────────────────────────────────────────────────
class TestGetStatus:

    EXPECTED_KEYS = {
        "timestamp", "status", "core_temp", "neutron_flux", "k_eff",
        "control_rods", "r_plasma", "phase_noise", "generated_power",
        "magnetic_residual",
    }

    def test_returns_all_keys(self):
        r = make_reactor()
        status = r.get_status()
        assert self.EXPECTED_KEYS == set(status.keys())

    def test_temp_is_float(self):
        r = make_reactor()
        assert isinstance(r.get_status()["core_temp"], float)

    def test_status_is_string(self):
        r = make_reactor()
        assert isinstance(r.get_status()["status"], str)


# ── _tick_physics (SCRAM path) ────────────────────────────────────────────────
class TestTickPhysicsScram:

    def test_scram_halves_neutron_flux(self):
        r = make_reactor()
        r.status_code = "SCRAM"
        r.neutron_flux = 10.0
        r._tick_physics()
        assert r.neutron_flux == pytest.approx(5.0)

    def test_scram_zeroes_keff(self):
        r = make_reactor()
        r.status_code = "SCRAM"
        r.k_eff = 1.5
        r._tick_physics()
        assert r.k_eff == 0.0

    def test_scram_shuts_down_when_flux_low(self):
        r = make_reactor()
        r.status_code = "SCRAM"
        r.is_running = True
        r.neutron_flux = 0.5   # Already below 1.0
        r._tick_physics()
        assert r.status_code == "OFFLINE"
        assert not r.is_running
