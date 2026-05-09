from collections import deque
from app.core.logger import get_logger

logger = get_logger(__name__)

class DeepGuardian:
    def __init__(self):
        self.look_back = 5
        self.is_trained = True
        self.realtime_buffer = deque(maxlen=self.look_back)

    def initialize(self):
        """Khởi tạo mô hình AI (bản thu gọn không dùng TensorFlow để tiết kiệm RAM)."""
        logger.info("[DEEP CORE] 🧠 DeepGuardian initialized in LITE mode (Heuristics only).")

    def _extract_features(self, sensors):
        if not sensors:
            return [0, 0, 0, 0, 0]

        avg_energy = sum(s.get("energy_level", 0) for s in sensors) / len(sensors)
        avg_anomaly = sum(s.get("anomaly_score", 0) for s in sensors) / len(sensors)
        max_mag = max(s.get("raw_val", 0) for s in sensors)
        event_count_norm = min(len(sensors) / 200.0, 1.0)

        cosmic_energy = 0.0
        for s in sensors:
            if s.get("type") == "SOLAR_FLARE":
                cosmic_energy = max(cosmic_energy, s.get("energy_level", 0))

        return [avg_energy, avg_anomaly, max_mag / 10.0, event_count_norm, cosmic_energy]

    def train_from_memory(self):
        logger.info("[DEEP CORE] LITE mode does not require MongoDB training.")
        return 0

    def update_realtime_state(self, sensors):
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        logger.debug(f"[DEEP CORE] Realtime buffer updated: {features}")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Predicted Risk = Heuristic calculation (falls back to formula-based estimate).
        """
        base_risk = local_energy * 0.7 + local_anomaly * 0.3
        
        if len(self.realtime_buffer) == 0:
            return base_risk

        # Simulate global instability from buffer
        recent_features = self.realtime_buffer[-1]
        global_instability = (recent_features[0] + recent_features[1]) / 2.0
        
        final_risk = global_instability * 0.4 + base_risk * 0.6
        return min(final_risk, 1.0)

guardian_brain = DeepGuardian()