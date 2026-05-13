import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import MinMaxScaler
from collections import deque

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)

class DeepGuardian:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 20  # Tăng lên 20 để có tầm nhìn dài hơn (Time-Series)
        self.is_trained = False
        
        # HistGradientBoostingRegressor: siêu tiết kiệm RAM và cực kỳ mạnh mẽ
        self.model = HistGradientBoostingRegressor(
            max_iter=200, 
            learning_rate=0.1,
            max_depth=5,
            random_state=42
        )

        self.realtime_buffer = deque(maxlen=self.look_back)

    def initialize(self):
        """Khởi tạo AI và huấn luyện từ MongoDB."""
        logger.info("[DEEP CORE] 🧠 DeepGuardian initialized. Connecting to memory...")
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
        
        # An toàn khi list rỗng
        max_mag = 0.0
        try:
            max_mag = max(s.get("raw_val", 0) for s in sensors)
        except ValueError:
            pass
            
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
            # Tăng dữ liệu lên 3000 vì Gradient Boosting xử lý rất nhanh mà không tốn RAM
            logs = list(col.find().sort("timestamp", -1).limit(3000))
            logs.reverse() # chronologically ascending
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
        # Kỹ thuật Trượt Cửa Sổ (Time-Series Windowing)
        for i in range(self.look_back, len(dataset_scaled)):
            window = dataset_scaled[i - self.look_back: i, :]
            X.append(window.flatten())
            # Target: Dự đoán mức độ rủi ro chung của chu kỳ kế tiếp (dựa vào max_mag và anomaly)
            target_risk = (dataset_scaled[i, 1] + dataset_scaled[i, 2]) / 2.0
            y.append(target_risk)

        self.model.fit(np.array(X), np.array(y))
        self.is_trained = True
        logger.info(
            f"[DEEP CORE] ✅ LITE Training complete — {len(X)} sequences learned from memory using HistGradientBoosting."
        )
        return len(X)

    def update_realtime_state(self, sensors):
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        logger.debug(f"[DEEP CORE] Realtime buffer updated. Size: {len(self.realtime_buffer)}/{self.look_back}")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Predicted Risk = Global Instability (Gradient Boosting) × Local Vulnerability factor.
        """
        if len(self.realtime_buffer) < self.look_back:
            return local_energy * 0.7 + local_anomaly * 0.3

        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            # Làm phẳng cửa sổ
            input_flattened = seq_scaled.flatten().reshape(1, -1)
            global_instability = float(self.model.predict(input_flattened)[0])
            # Giảm độ nhạy: Cân bằng 70% bất ổn toàn cầu và 30% rủi ro cục bộ thay vì nhân hệ số
            final_risk = (global_instability * 0.7) + (local_energy * 0.3)
            
            # Đảm bảo rủi ro từ 0 -> 1
            return min(max(final_risk, 0.0), 1.0)

        except Exception as e:
            logger.error(f"[DEEP CORE] Gradient Boosting prediction failed: {e}", exc_info=True)
            return 0.5

guardian_brain = DeepGuardian()