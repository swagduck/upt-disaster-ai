import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from collections import deque

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)


class DeepGuardian:
    def __init__(self):
        self.model_path = "app/upt_engine/guardian_lstm.keras"
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 5
        self.is_trained = False
        self.model = None

        # Buffer stores the global real-time state (updated by EarthquakeService)
        self.realtime_buffer = deque(maxlen=self.look_back)

    def initialize(self):
        """Khởi tạo mô hình TensorFlow và huấn luyện từ MongoDB bất đồng bộ (tránh treo lúc khởi động)"""
        try:
            # TensorFlow device config
            gpus = tf.config.list_physical_devices("GPU")
            if gpus:
                logger.info(f"[DEEP CORE] 🚀 NVIDIA GPU Active: {len(gpus)} device(s).")
            else:
                logger.warning("[DEEP CORE] No GPU found — running in CPU Mode.")

            self._build_brain()

            if Database.db is not None:
                logger.info("[DEEP CORE] 🧠 Loading memory patterns from MongoDB...")
                self.train_from_memory()
        except Exception as e:
            logger.error(f"[DEEP CORE] Error during async initialization: {e}", exc_info=True)

    def _build_brain(self):
        self.model = tf.keras.models.Sequential()
        self.model.add(tf.keras.layers.Input(shape=(self.look_back, 5)))
        self.model.add(tf.keras.layers.LSTM(units=64, return_sequences=True))
        self.model.add(tf.keras.layers.Dropout(0.2))
        self.model.add(tf.keras.layers.LSTM(units=32))
        self.model.add(tf.keras.layers.Dropout(0.2))
        self.model.add(tf.keras.layers.Dense(1, activation="sigmoid"))
        self.model.compile(optimizer="adam", loss="binary_crossentropy")
        logger.debug("[DEEP CORE] LSTM model architecture built.")

    def _extract_features(self, sensors):
        """Extract a 5-dimensional feature vector from a sensor list."""
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
            logs = list(col.find().sort("timestamp", 1).limit(1000))
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
        for i in range(self.look_back, len(dataset_scaled)):
            X.append(dataset_scaled[i - self.look_back: i, :])
            y.append(dataset_scaled[i, 2])  # Target: next MaxMag

        self.model.fit(np.array(X), np.array(y), epochs=3, batch_size=4, verbose=0)
        self.is_trained = True
        logger.info(
            f"[DEEP CORE] ✅ Training complete — {len(X)} sequences learned from memory."
        )
        return len(X)

    def update_realtime_state(self, sensors):
        """Called by EarthquakeService whenever fresh data arrives."""
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        logger.debug(f"[DEEP CORE] Realtime buffer updated: {features}")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Predicted Risk = Global Instability (LSTM) × Local Vulnerability factor.
        Falls back to formula-based estimate when buffer is insufficient.
        """
        if len(self.realtime_buffer) < self.look_back:
            logger.debug(
                "[DEEP CORE] Buffer not yet full — using fallback formula."
            )
            return local_energy * 0.7 + local_anomaly * 0.3

        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            input_reshaped = np.reshape(seq_scaled, (1, self.look_back, 5))
            global_instability = float(
                self.model.predict(input_reshaped, verbose=0)[0][0]
            )
            final_risk = global_instability * (0.5 + local_energy)
            return min(final_risk, 1.0)

        except Exception as e:
            logger.error(f"[DEEP CORE] LSTM prediction failed: {e}", exc_info=True)
            return 0.5


guardian_brain = DeepGuardian()