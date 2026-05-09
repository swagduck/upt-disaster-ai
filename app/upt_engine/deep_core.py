import numpy as np
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import MinMaxScaler
from collections import deque

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)

class DeepGuardian:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 5
        self.is_trained = False
        
        # MLP Neural Network (Lightweight AI)
        self.model = MLPRegressor(
            hidden_layer_sizes=(32, 16),
            max_iter=50, # Fast training
            random_state=42
        )

        self.realtime_buffer = deque(maxlen=self.look_back)

    def initialize(self):
        """Khởi tạo mô hình AI Lightweight (MLP) và huấn luyện từ MongoDB."""
        logger.info("[DEEP CORE] 🧠 DeepGuardian LITE initialized. Connecting to memory...")
        try:
            if Database.db is not None:
                self.train_from_memory()
        except Exception as e:
            logger.error(f"[DEEP CORE] Initialization error: {e}")

    def _extract_features(self, sensors):
        if not sensors:
            return [0, 0, 0, 0, 0]

        avg_energy = np.mean([s.get("energy_level", 0) for s in sensors])
        avg_anomaly = np.mean([s.get("anomaly_score", 0) for s in sensors])
        max_mag = max(s.get("raw_val", 0) for s in sensors)
        event_count_norm = min(len(sensors) / 200.0, 1.0)

        cosmic_energy = 0.0
        for s in sensors:
            if s.get("type") == "SOLAR_FLARE":
                cosmic_energy = max(cosmic_energy, s.get("energy_level", 0))

        return [avg_energy, avg_anomaly, max_mag / 10.0, event_count_norm, cosmic_energy]

    def train_from_memory(self):
        col = Database.get_collection("raw_logs")
        if col is None:
            return 0

        try:
            logs = list(col.find().sort("timestamp", -1).limit(1000))
            logs.reverse() # chronological order
        except Exception as e:
            logger.error(f"[DEEP CORE] Failed to read training data from DB: {e}")
            return 0

        if len(logs) < self.look_back + 10:
            logger.warning(
                f"[DEEP CORE] Insufficient DB records ({len(logs)}) "
                f"— minimum {self.look_back + 10} required for training."
            )
            return 0

        data = []
        for log in logs:
            sensors = log.get("sensors_data", [])
            features = self._extract_features(sensors)
            data.append(features)

        dataset = np.array(data)
        self.scaler.fit(dataset)
        dataset_scaled = self.scaler.transform(dataset)

        X, y = [], []
        # Flatten the look_back window into a 1D array of look_back*5 size
        for i in range(self.look_back, len(dataset_scaled)):
            window = dataset_scaled[i - self.look_back: i, :]
            X.append(window.flatten())
            y.append(dataset_scaled[i, 2])  # Target: next MaxMag

        self.model.fit(np.array(X), np.array(y))
        self.is_trained = True
        logger.info(
            f"[DEEP CORE] ✅ LITE Training complete — {len(X)} sequences learned from memory."
        )
        return len(X)

    def update_realtime_state(self, sensors):
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        logger.debug(f"[DEEP CORE] Realtime buffer updated.")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Predicted Risk = Global Instability (MLP) × Local Vulnerability factor.
        Falls back to formula-based estimate when buffer is insufficient.
        """
        if len(self.realtime_buffer) < self.look_back:
            return local_energy * 0.7 + local_anomaly * 0.3

        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            # Flatten window to 1D
            input_flattened = seq_scaled.flatten().reshape(1, -1)
            global_instability = float(self.model.predict(input_flattened)[0])
            final_risk = global_instability * (0.5 + local_energy)
            return min(final_risk, 1.0)

        except Exception as e:
            logger.error(f"[DEEP CORE] MLP prediction failed: {e}", exc_info=True)
            return 0.5

guardian_brain = DeepGuardian()