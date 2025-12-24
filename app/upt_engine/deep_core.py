import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from collections import deque
from app.core.database import Database

class DeepGuardian:
    def __init__(self):
        self.model_path = "app/upt_engine/guardian_lstm.keras"
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 5 
        self.is_trained = False
        self.model = None
        
        # Buffer lưu trữ trạng thái TOÀN CẦU thực tế (được cập nhật bởi EarthquakeService)
        self.realtime_buffer = deque(maxlen=self.look_back)
        
        # Config TF
        gpus = tf.config.list_physical_devices('GPU')
        if gpus: print(f"🚀 [DEEP CORE] NVIDIA GPU Active: {len(gpus)} device(s).")
        else: print("⚠️ [DEEP CORE] Running on CPU Mode.")

        self._build_brain()
        
        if Database.db is not None:
            print("🧠 [DEEP CORE] Loading REAL Memory Patterns from DB...")
            self.train_from_memory()
        
    def _build_brain(self):
        self.model = tf.keras.models.Sequential()
        self.model.add(tf.keras.layers.Input(shape=(self.look_back, 5)))
        
        self.model.add(tf.keras.layers.LSTM(units=64, return_sequences=True))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.LSTM(units=32))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.Dense(1, activation='sigmoid'))
        self.model.compile(optimizer='adam', loss='binary_crossentropy')

    def _extract_features(self, sensors):
        """Hàm helper để trích xuất 5 chỉ số thực từ danh sách sensors"""
        if not sensors: return [0,0,0,0,0]
        
        avg_energy = np.mean([s.get('energy_level', 0) for s in sensors])
        avg_anomaly = np.mean([s.get('anomaly_score', 0) for s in sensors])
        max_mag = max([s.get('raw_val', 0) for s in sensors])
        
        # Normalize event count (Giả sử 200 event là mốc cao)
        event_count_norm = min(len(sensors) / 200.0, 1.0)
        
        # Lấy năng lượng vũ trụ (Solar Flare)
        cosmic_energy = 0.0
        for s in sensors:
            if s.get('type') == 'SOLAR_FLARE':
                cosmic_energy = max(cosmic_energy, s.get('energy_level', 0))
                
        # Vector 5 chiều THỰC TẾ
        return [avg_energy, avg_anomaly, max_mag/10.0, event_count_norm, cosmic_energy]

    def train_from_memory(self):
        col = Database.get_collection("raw_logs")
        if col is None: return 0
        
        try: logs = list(col.find().sort("timestamp", 1).limit(1000))
        except: return 0
        
        if len(logs) < self.look_back + 10: return 0
        
        data = []
        for log in logs:
            sensors = log.get('sensors_data', [])
            features = self._extract_features(sensors)
            data.append(features)

        dataset = np.array(data)
        self.scaler.fit(dataset) # Fit scaler với dữ liệu thật
        dataset_scaled = self.scaler.transform(dataset)
        
        X, y = [], []
        for i in range(self.look_back, len(dataset_scaled)):
            X.append(dataset_scaled[i-self.look_back:i, :])
            # Target: Dự đoán MaxMag tiếp theo (hoặc mức độ bất ổn)
            y.append(dataset_scaled[i, 2]) 
            
        self.model.fit(np.array(X), np.array(y), epochs=3, batch_size=4, verbose=0)
        self.is_trained = True
        return len(X)

    def update_realtime_state(self, sensors):
        """Được gọi bởi EarthquakeService mỗi khi có dữ liệu mới"""
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        # print(f"🧠 [AI MEMORY] Buffer updated with REAL state: {features}")

    def learn(self, sensors):
        return self.update_realtime_state(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        """
        Dự báo Rủi ro = (Bất ổn Toàn cầu từ LSTM) * (Mức độ tổn thương Cục bộ)
        """
        # Nếu chưa có đủ dữ liệu toàn cầu -> Fallback
        if len(self.realtime_buffer) < self.look_back:
            return (local_energy * 0.7 + local_anomaly * 0.3)
            
        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            # 1. Lấy bối cảnh toàn cầu từ Buffer (REAL DATA)
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            input_reshaped = np.reshape(seq_scaled, (1, self.look_back, 5))
            
            # 2. AI dự đoán mức độ bất ổn toàn cầu (0.0 - 1.0)
            global_instability = float(self.model.predict(input_reshaped, verbose=0)[0][0])
            
            # 3. Kết hợp với dữ liệu cục bộ (Local Context)
            # Công thức: Risk = Global_Instability * (1 + Local_Energy)
            # Ý nghĩa: Nếu thế giới bất ổn, một chấn động nhỏ ở địa phương cũng có thể gây sụp đổ
            final_risk = global_instability * (0.5 + local_energy)
            
            return min(final_risk, 1.0)
            
        except Exception as e:
            print(f"LSTM Error: {e}")
            return 0.5

guardian_brain = DeepGuardian()