import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import os
import joblib

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)


class GuardianAI:
    def __init__(self):
        self.scaler = StandardScaler()
        # Random Forest: robust, multi-purpose regressor
        self.model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.is_trained = False

        # Pacific Ring of Fire — key geological fault coordinates
        self.fault_lines = [
            [36.2, 138.2],   # Japan
            [37.7, -122.4],  # San Francisco
            [-33.4, -70.6],  # Santiago
            [-6.2, 106.8],   # Jakarta
            [14.0, 121.0],   # Philippines
            [-41.2, 174.7],  # Wellington
            [35.0, 25.0],    # Crete
            [28.0, 84.0],    # Nepal
        ]

        # In-memory training buffers
        self.X_buffer = []
        self.y_buffer = []

        # Smart startup: try history first, fall back to safe mode
        if Database.db is not None:
            logger.info("[NEURAL CORE] ⏳ Mining historical data from MongoDB...")
            count = self.train_from_history()

            if count > 10:
                logger.info(
                    f"[NEURAL CORE] 🧠 Trained on {count} historical snapshots "
                    f"(Time-Travel Mode active)."
                )
            else:
                self._init_safe_mode()
        else:
            self._init_safe_mode()

    def _get_distance_to_fault(self, lat: float, lon: float) -> float:
        """Euclidean distance (km) to the nearest known fault line."""
        min_dist = 99999.0
        for f_lat, f_lon in self.fault_lines:
            dist = np.sqrt((lat - f_lat) ** 2 + (lon - f_lon) ** 2) * 111.0
            if dist < min_dist:
                min_dist = dist
        return min_dist

    def _init_safe_mode(self):
        """
        Initialise with a zero-vector so Scaler/Model are fitted and
        the app never crashes — but mark is_trained=False for callers.
        """
        logger.warning(
            "[NEURAL CORE] No training history available — "
            "running in SAFE MODE (waiting for data)."
        )
        self.X_buffer = [[0.0, 0.0, 0.0, 0.0, 0.0]]
        self.y_buffer = [0.0]
        self.scaler.fit(self.X_buffer)
        self.model.fit(self.scaler.transform(self.X_buffer), self.y_buffer)
        self.is_trained = False

    def train_from_history(self) -> int:
        """
        Supervised learning: Input(T) → Output(T+24h).
        Returns the number of training samples generated.
        """
        col = Database.get_collection("raw_logs")
        if col is None:
            return 0

        try:
            logs = list(col.find().sort("timestamp", 1).limit(1000))
        except Exception as e:
            logger.error(f"[NEURAL CORE] DB read error during training: {e}")
            return 0

        if len(logs) < 5:
            logger.debug("[NEURAL CORE] Fewer than 5 log records — skipping training.")
            return 0

        X_history, y_history = [], []

        for i, current_log in enumerate(logs):
            current_time = current_log.get("timestamp")
            if not current_time:
                continue

            # Find the largest event in the next 24 h
            future_max_mag = 0.0
            found_future = False
            for j in range(i + 1, len(logs)):
                future_log = logs[j]
                future_time = future_log.get("timestamp")
                if not future_time:
                    continue
                time_diff = (future_time - current_time).total_seconds()
                if time_diff > 24 * 3600:
                    break
                mag = future_log.get("max_magnitude", 0)
                if mag > future_max_mag:
                    future_max_mag = mag
                    found_future = True

            if not found_future:
                continue

            sensors = current_log.get("sensors_data", [])
            if not sensors:
                continue

            for s in sensors[:20]:
                if "lat" not in s or "lon" not in s:
                    continue
                dist = self._get_distance_to_fault(s["lat"], s["lon"])
                X_history.append([
                    s["lat"], s["lon"],
                    s.get("energy_level", 0),
                    s.get("anomaly_score", 0),
                    dist,
                ])
                y_history.append(min(1.0, future_max_mag / 9.0))

        if not X_history:
            logger.warning("[NEURAL CORE] No valid training samples extracted from logs.")
            return 0

        X = np.array(X_history)
        y = np.array(y_history)
        self.scaler.fit(X)
        self.model.fit(self.scaler.transform(X), y)
        self.is_trained = True
        logger.info(f"[NEURAL CORE] ✅ RandomForest trained on {len(X_history)} samples.")
        return len(X_history)

    def learn(self, sensors_data):
        # Primary learning path goes through train_from_history (DB-backed).
        # This stub is kept for API compatibility.
        return 0

    def predict_risk(self, lat: float, lon: float, energy: float, anomaly: float) -> float:
        """
        Predict seismic risk at a given coordinate.
        Falls back to a weighted formula if the model is not yet trained.
        """
        if not self.is_trained:
            return energy * 0.7 + anomaly * 0.3

        try:
            dist = self._get_distance_to_fault(lat, lon)
            input_data = np.array([[lat, lon, energy, anomaly, dist]])
            scaled_input = self.scaler.transform(input_data)
            prediction = self.model.predict(scaled_input)[0]
            return float(max(0.0, min(1.0, prediction)))
        except Exception as e:
            logger.error(f"[NEURAL CORE] Prediction failed: {e}", exc_info=True)
            return 0.0


guardian_brain = GuardianAI()