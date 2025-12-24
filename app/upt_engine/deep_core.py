import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from collections import deque
from app.core.database import Database

class DeepGuardian:
    def __init__(self):
        self.model_path = "app/upt_engine/guardian_lstm.keras"
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 5 # AI nhìn lại 5 bước thời gian
        self.is_trained = False
        self.model = None
        
        # --- BUFFER BỘ NHỚ THỰC TẾ ---
        self.realtime_buffer = deque(maxlen=self.look_back)
        
        # Kiểm tra GPU
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"🚀 [DEEP CORE] NVIDIA GPU Active: {len(gpus)} device(s).")
        else:
            print("⚠️ [DEEP CORE] Running on CPU Mode.")

        self._build_brain()
        
        # Khởi động: Train từ DB
        if Database.db is not None:
            print("🧠 [DEEP CORE] Loading Memory Patterns...")
            self.train_from_memory()
        
    def _build_brain(self):
        """LSTM Architecture"""
        self.model = tf.keras.models.Sequential()
        self.model.add(tf.keras.layers.Input(shape=(self.look_back, 5)))
        
        self.model.add(tf.keras.layers.LSTM(units=64, return_sequences=True))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.LSTM(units=32))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.Dense(1, activation='sigmoid'))
        
        self.model.compile(optimizer='adam', loss='binary_crossentropy')

    def train_from_memory(self):
        """Train lại model từ lịch sử MongoDB"""
        col = Database.get_collection("raw_logs")
        if col is None: return 0
        
        try:
            logs = list(col.find().sort("timestamp", 1).limit(1000))
        except: return 0
        
        if len(logs) < self.look_back + 10: return 0
        
        data = []
        for log in logs:
            sensors = log.get('sensors_data', [])
            avg_energy = np.mean([s.get('energy_level', 0) for s in sensors]) if sensors else 0
            avg_anomaly = np.mean([s.get('anomaly_score', 0) for s in sensors]) if sensors else 0
            max_mag = log.get('max_magnitude', 0)
            data.append([avg_energy, avg_anomaly, max_mag, 0.5, 0.5])

        dataset = np.array(data)
        self.scaler.fit(dataset)
        dataset_scaled = self.scaler.transform(dataset)
        
        X, y = [], []
        for i in range(self.look_back, len(dataset_scaled)):
            X.append(dataset_scaled[i-self.look_back:i, :])
            y.append(dataset_scaled[i, 2]) 
            
        X, y = np.array(X), np.array(y)
        
        self.model.fit(X, y, epochs=3, batch_size=4, verbose=0)
        self.is_trained = True
        return len(X)

    # --- 👇 BỔ SUNG QUAN TRỌNG: HÀM WRAPPER ĐỂ SỬA LỖI API 👇 ---
    def learn(self, sensors_data=None):
        """
        Hàm tương thích ngược (Backward Compatibility).
        API prediction.py vẫn gọi hàm này. Chúng ta trỏ nó về train_from_memory.
        """
        return self.train_from_memory()
    # ------------------------------------------------------------

    def predict_risk(self, lat, lon, energy, anomaly):
        """Dự đoán rủi ro dựa trên chuỗi dữ liệu thực tế."""
        current_features = [energy, anomaly, 0.5, 0.5, 0.5]
        self.realtime_buffer.append(current_features)
        
        if len(self.realtime_buffer) < self.look_back:
            return (energy * 0.7 + anomaly * 0.3)
            
        if not self.is_trained:
            return (energy + anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            input_reshaped = np.reshape(seq_scaled, (1, self.look_back, 5))
            
            prediction = self.model.predict(input_reshaped, verbose=0)
            return float(prediction[0][0])
            
        except Exception as e:
            print(f"LSTM Error: {e}")
            return 0.5

# Singleton
guardian_brain = DeepGuardian()