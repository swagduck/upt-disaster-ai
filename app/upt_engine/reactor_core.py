import asyncio
import random
import math
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


class UPTReactorCore:
    """
    UPT-RC: Resonance Containment Reactor Core (Production Grade)
    """
    # GOLDEN BUILD PARAMETERS
    CONST_C_GEO = 0.911
    CONST_TAU_ION = 0.080
    CONST_RES_FREQ = 2.148

    def __init__(self):
        self.is_running = False
        self.status_code = "OFFLINE"

        # Physics State
        self.core_temp = 300.0
        self.neutron_flux = 0.0
        self.k_eff = 0.0
        self.r_plasma = 0.0

        # Control Systems
        self.control_rods = 100.0
        self.cryo_cooling = 100.0

        # Environment & Noise
        self.entropy_accumulation = 0.0
        self.phase_noise = 0.0

        # Geomagnetic residual — solar storms accumulate slowly over time
        self.geomagnetic_residual = 0.0

    def start_reactor(self):
        if not self.is_running:
            self.is_running = True
            self.status_code = "STARTUP"
            logger.info(
                f"[UPT-RC] ☢️  Ignition Sequence Initiated. "
                f"F_res locked at {self.CONST_RES_FREQ} GHz."
            )
            self.r_plasma = 0.5
            self.neutron_flux = 1.0
            asyncio.create_task(self._run_simulation_loop())

    def trigger_phase_detuning(self):
        if self.status_code == "SCRAM":
            return
        logger.critical("[UPT-RC] 🚨 EMERGENCY SCRAM: PHASE DE-TUNING SHOCK EXECUTED!")
        self.status_code = "SCRAM"
        self.control_rods = 100.0
        self.phase_noise = 10.0
        self.r_plasma = 0.0

    def inject_cosmic_interference(self, coupling_factor: float):
        """
        Receive a solar storm signal.
        Instead of instant shock, it accumulates into geomagnetic_residual —
        a 'butterfly effect' that slowly destabilises the reactor.
        """
        if coupling_factor > 0.05:
            logger.warning(
                f"[UPT-RC] ⚠️  COSMIC INTERFERENCE DETECTED. "
                f"Coupling Factor: {coupling_factor:.4f}"
            )
            self.geomagnetic_residual += coupling_factor

    def update_external_stress(self, stress_level: float):
        """Direct physical impact from seismic events."""
        if stress_level > 0.5:
            logger.warning(f"[UPT-RC] ⚠️  Seismic Wave Impact: {stress_level:.4f}")
            self.phase_noise += stress_level * 0.5

    async def _run_simulation_loop(self):
        while self.is_running:
            try:
                self._tick_physics()
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"[UPT-RC] Simulation loop error: {e}", exc_info=True)
                await asyncio.sleep(1)

    def _tick_physics(self):
        if self.status_code == "SCRAM":
            self.neutron_flux *= 0.5
            self.core_temp += (300 - self.core_temp) * 0.1
            self.k_eff = 0
            if self.neutron_flux < 1.0:
                self.is_running = False
                self.status_code = "OFFLINE"
                logger.info("[UPT-RC] Reactor safely shut down — status OFFLINE.")
            return

        # 1. Geomagnetic residual decay (1% per tick — long-term destabiliser)
        self.geomagnetic_residual *= 0.99

        # 2. Phase noise synthesis
        quantum_noise = random.uniform(-0.01, 0.01)
        self.phase_noise = abs(quantum_noise + (self.geomagnetic_residual * 2.0))
        if self.phase_noise > 2.0:
            self.phase_noise *= 0.9  # Stability system kicks in

        # 3. K_eff Calculation (UPT Formula)
        ai_damp = (self.control_rods / 100.0) * 0.5
        e_p = (self.neutron_flux / 50.0) + self.CONST_TAU_ION
        r_eff = self.r_plasma
        numerator = e_p * self.CONST_C_GEO * r_eff
        denominator = 1.0 + self.phase_noise + ai_damp
        self.k_eff = numerator / denominator if denominator > 0 else 0

        # 4. Neutron Flux Dynamics
        if self.neutron_flux < 1.0:
            self.neutron_flux = 1.0
        delta_flux = self.neutron_flux * (self.k_eff - 1.0) * 0.5
        self.neutron_flux = max(0.0, self.neutron_flux + delta_flux)

        # 5. Thermodynamics
        heat_gen = self.neutron_flux * 5.0
        cooling_cap = self.cryo_cooling * 4.0
        self.core_temp += (heat_gen - cooling_cap) * 0.1
        if self.core_temp < 300:
            self.core_temp = 300

        # 6. Resonance Stability (R_plasma)
        stability_delta = 0.01
        if self.phase_noise > 0.1:
            stability_delta -= 0.05
        self.r_plasma = max(0.0, min(1.0, self.r_plasma + stability_delta))

        # 7. Status Logic
        prev_status = self.status_code
        if self.core_temp > 2500 or self.r_plasma < 0.2:
            self.status_code = "CRITICAL"
        elif (self.core_temp > 1500
              or self.r_plasma < 0.6
              or self.geomagnetic_residual > 0.5):
            self.status_code = "WARNING"
        else:
            self.status_code = "NOMINAL"

        if self.status_code != prev_status:
            logger.warning(
                f"[UPT-RC] Status changed: {prev_status} → {self.status_code} | "
                f"T={self.core_temp:.1f}K  R={self.r_plasma:.3f}  "
                f"MagRes={self.geomagnetic_residual:.3f}"
            )

        # Safety Protocol — random SCRAM on sustained CRITICAL
        if self.status_code == "CRITICAL" and random.random() < 0.1:
            self.trigger_phase_detuning()

    def get_status(self):
        return {
            "timestamp": datetime.now().isoformat(),
            "status": self.status_code,
            "core_temp": round(self.core_temp, 1),
            "neutron_flux": round(self.neutron_flux, 2),
            "k_eff": round(self.k_eff, 4),
            "control_rods": round(self.control_rods, 1),
            "r_plasma": round(self.r_plasma, 4),
            "phase_noise": round(self.phase_noise, 3),
            "generated_power": round(self.neutron_flux * 5, 2),
            "magnetic_residual": round(self.geomagnetic_residual, 3),
        }


upt_reactor = UPTReactorCore()