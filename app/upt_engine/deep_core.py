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
        # Lưu trữ dòng dữ liệu realtime để tạo sequence cho LSTM
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
        
        # Tầng LSTM sâu hơn để bắt pattern phức tạp
        self.model.add(tf.keras.layers.LSTM(units=64, return_sequences=True))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.LSTM(units=32))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.Dense(1, activation='sigmoid')) # Output 0-1 (Risk Score)
        
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
            # Feature Extraction
            sensors = log.get('sensors_data', [])
            avg_energy = np.mean([s.get('energy_level', 0) for s in sensors]) if sensors else 0
            avg_anomaly = np.mean([s.get('anomaly_score', 0) for s in sensors]) if sensors else 0
            # Target giả định: Nếu max_magnitude > 5.0 thì là High Risk (1.0)
            max_mag = log.get('max_magnitude', 0)
            
            # Vector [Energy, Anomaly, Mag, Flux(Mock), RandomBias]
            data.append([avg_energy, avg_anomaly, max_mag, 0.5, 0.5])

        dataset = np.array(data)
        # Fit scaler
        self.scaler.fit(dataset)
        dataset_scaled = self.scaler.transform(dataset)
        
        X, y = [], []
        for i in range(self.look_back, len(dataset_scaled)):
            X.append(dataset_scaled[i-self.look_back:i, :])
            # Target: Nếu Mag > 0.5 (sau scale) thì Risk = 1
            y.append(dataset_scaled[i, 2]) 
            
        X, y = np.array(X), np.array(y)
        
        self.model.fit(X, y, epochs=3, batch_size=4, verbose=0)
        self.is_trained = True
        return len(X)

    def predict_risk(self, lat, lon, energy, anomaly):
        """
        Dự đoán rủi ro dựa trên chuỗi dữ liệu thực tế (Real-time Sequence).
        """
        # Tạo vector feature hiện tại
        # [Energy, Anomaly, PlaceholderMag, PlaceholderFlux, PlaceholderBias]
        current_features = [energy, anomaly, 0.5, 0.5, 0.5]
        
        # 1. Cập nhật bộ nhớ ngắn hạn
        self.realtime_buffer.append(current_features)
        
        # Nếu chưa đủ dữ liệu lịch sử (lúc mới khởi động), dùng thuật toán thô
        if len(self.realtime_buffer) < self.look_back:
            return (energy * 0.7 + anomaly * 0.3)
            
        if not self.is_trained:
            return (energy + anomaly) / 2.0

        try:
            # 2. Chuẩn bị Input cho LSTM
            # Lấy toàn bộ buffer làm sequence
            raw_seq = np.array(list(self.realtime_buffer))
            
            # Scale dữ liệu (Dùng scaler đã fit lúc train, hoặc partial_fit nếu cần)
            # Ở đây giả định scaler đã được fit hoặc dùng range mặc định
            seq_scaled = self.scaler.transform(raw_seq)
            
            # Reshape (1, look_back, 5)
            input_reshaped = np.reshape(seq_scaled, (1, self.look_back, 5))
            
            # 3. Dự đoán
            prediction = self.model.predict(input_reshaped, verbose=0)
            risk_score = float(prediction[0][0])
            
            return risk_score
            
        except Exception as e:
            print(f"LSTM Error: {e}")
            return 0.5

# Singleton
guardian_brain = DeepGuardian()