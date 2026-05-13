import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
from collections import deque

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)

class DeepGuardian:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 20  # Tăng lên 20 để có tầm nhìn dài hơn (Time-Series)
        self.is_trained = False
        self.metrics = {"mse": 0.0, "mae": 0.0, "accuracy_score": 0.0}
        
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
        # Kỹ thuật Trượt Cửa Sổ (Time-Series Windowing) với Tầm nhìn Tương lai (Forecast Horizon)
        forecast_horizon = 5  # Dự đoán xa hơn 5 nhịp thời gian vào tương lai
        
        for i in range(self.look_back, len(dataset_scaled) - forecast_horizon):
            window = dataset_scaled[i - self.look_back: i, :]
            X.append(window.flatten())
            # Target: Dự đoán mức độ rủi ro chung ở TƯƠNG LAI (i + forecast_horizon)
            target_risk = (dataset_scaled[i + forecast_horizon, 1] + dataset_scaled[i + forecast_horizon, 2]) / 2.0
            y.append(target_risk)

        X = np.array(X)
        y = np.array(y)

        # Chia dữ liệu theo thời gian (Chronological Split): 80% học, 20% mới nhất để thi
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        if len(X_train) == 0 or len(X_test) == 0:
            # Fallback nếu dữ liệu quá ít
            self.model.fit(X, y)
            self.is_trained = True
            self.evaluate_accuracy(X, y)
        else:
            self.model.fit(X_train, y_train)
            self.is_trained = True
            logger.info(
                f"[DEEP CORE] ✅ Training complete: {len(X_train)} train samples. Evaluation on {len(X_test)} test samples."
            )
            # Đánh giá ĐỘ CHÍNH XÁC THỰC TẾ trên tập Test (dữ liệu tương lai giả lập)
            self.evaluate_accuracy(X_test, y_test)
        
        
        return len(X)

    def evaluate_accuracy(self, X, y):
        """Đánh giá độ chính xác của AI trên tập dữ liệu."""
        if len(X) == 0:
            return
            
        try:
            preds = self.model.predict(np.array(X))
            mse = mean_squared_error(y, preds)
            mae = mean_absolute_error(y, preds)
            
            # Tính điểm Accuracy Score tương đối (1 - sai số tuyệt đối trung bình so với biên độ)
            # Vì target y nằm trong khoảng [0, 1] nên max error có thể là 1.
            accuracy_score = max(0.0, (1.0 - mae)) * 100
            
            self.metrics = {
                "mse": round(mse, 4),
                "mae": round(mae, 4),
                "accuracy_score": round(accuracy_score, 2)
            }
            logger.info(f"[DEEP CORE] AI Accuracy Evaluated: {self.metrics['accuracy_score']}% (MSE={self.metrics['mse']})")
        except Exception as e:
            logger.error(f"[DEEP CORE] Evaluation failed: {e}")

    def update_realtime_state(self, sensors):
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        logger.debug(f"[DEEP CORE] Realtime buffer updated. Size: {len(self.realtime_buffer)}/{self.look_back}")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Predicted Risk = Global Instability (Gradient Boosting) + Location-Specific Factor.

        Công thức tái cân bằng:
          - global_instability (40%): Xu hướng bất ổn toàn cầu từ AI — giống nhau cho mọi vùng
            tại cùng một thời điểm, phản ánh "nhiệt độ" chung của hành tinh.
          - location_factor (60%): Tín hiệu ĐỊA PHƯƠNG riêng biệt của từng hotspot, kết hợp:
              • local_energy  (60% của 60%): Năng lượng pha trộn live + base_risk địa tầng
              • local_anomaly (40% của 60%): Mật độ dị thường cục bộ quanh tọa độ đó
        Tổng hợp: mỗi hotspot luôn cho ra điểm số riêng biệt, không bị san bằng bởi hệ số toàn cầu.
        """
        if len(self.realtime_buffer) < self.look_back:
            # Chưa đủ buffer: dựa hoàn toàn vào tín hiệu địa phương
            return min(local_energy * 0.6 + local_anomaly * 0.4, 1.0)

        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            input_flattened = seq_scaled.flatten().reshape(1, -1)
            global_instability = float(self.model.predict(input_flattened)[0])

            # Tín hiệu địa phương: kết hợp năng lượng pha trộn + dị thường cục bộ
            # local_energy ở đây là blended_energy (live * 0.65 + base_risk * 0.35)
            location_factor = (local_energy * 0.6) + (local_anomaly * 0.4)

            # Global trend (40%) + Location-specific signal (60%)
            # → Các vùng có base_risk / live events khác nhau sẽ phân hóa rõ rệt hơn
            final_risk = (global_instability * 0.4) + (location_factor * 0.6)

            # Đảm bảo rủi ro từ 0 -> 1
            return min(max(final_risk, 0.0), 1.0)

        except Exception as e:
            logger.error(f"[DEEP CORE] Gradient Boosting prediction failed: {e}", exc_info=True)
            return 0.5

guardian_brain = DeepGuardian()