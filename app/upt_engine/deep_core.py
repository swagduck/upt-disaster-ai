import numpy as np
import tensorflow as tf
import os
from sklearn.preprocessing import MinMaxScaler

# Import kết nối Database
from app.core.database import Database

class DeepGuardian:
    def __init__(self):
        self.model_path = "app/upt_engine/guardian_lstm.keras"
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 5 # AI sẽ nhìn lại 5 sự kiện gần nhất
        self.is_trained = False
        self.model = None
        
        # Kiểm tra GPU
        gpus = tf.config.list_physical_devices('GPU')
        if gpus:
            print(f"🚀 [DEEP CORE] NVIDIA GPU Detected: {len(gpus)} device(s).")
        else:
            print("⚠️ [DEEP CORE] GPU not found (or unsupported on native Windows). Running on CPU.")

        # Kiến trúc mạng Nơ-ron
        self._build_brain()
        
        # Khởi động: Train từ DB nếu có
        if Database.db is not None:
            print("🧠 [DEEP CORE] Initializing Neural Network (LSTM)...")
            count = self.train_from_memory()
            if count == 0:
                print("⚠️ [DEEP CORE] Insufficient data history. Standing by for live data...")
        
    def _build_brain(self):
        """
        Xây dựng kiến trúc mạng nơ-ron LSTM.
        Sử dụng tf.keras trực tiếp để tránh lỗi cảnh báo (lỗi vàng) trong IDE.
        """
        self.model = tf.keras.models.Sequential()
        
        # Input Layer (Dùng tf.keras.layers.Input)
        self.model.add(tf.keras.layers.Input(shape=(self.look_back, 5)))
        
        # Hidden Layers (Dùng tf.keras.layers.LSTM)
        self.model.add(tf.keras.layers.LSTM(units=50, return_sequences=True))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        self.model.add(tf.keras.layers.LSTM(units=50))
        self.model.add(tf.keras.layers.Dropout(0.2))
        
        # Output Layer
        self.model.add(tf.keras.layers.Dense(1))
        
        self.model.compile(optimizer='adam', loss='mean_squared_error')

    def train_from_memory(self):
        """Học từ lịch sử MongoDB (Sequence Learning)"""
        col = Database.get_collection("raw_logs")
        if col is None: return 0
        
        # Lấy 2000 bản ghi gần nhất
        try:
            logs = list(col.find().sort("timestamp", 1).limit(2000))
        except: return 0
        
        # Cần ít nhất (look_back + vài mẫu) để train
        if len(logs) < self.look_back + 5: return 0
        
        # 1. Chuẩn bị dữ liệu chuỗi (Time Series)
        time_series_data = []
        
        for log in logs:
            sensors = log.get('sensors_data', [])
            if not sensors: continue
            
            # Tính trung bình các chỉ số toàn cầu tại thời điểm T
            avg_energy = np.mean([s.get('energy_level', 0) for s in sensors])
            avg_anomaly = np.mean([s.get('anomaly_score', 0) for s in sensors])
            max_mag = log.get('max_magnitude', 0)
            event_count = log.get('total_events', 0)
            
            # Vector 5 chiều: [Energy, Anomaly, MaxMag, Count, Bias]
            time_series_data.append([avg_energy, avg_anomaly, max_mag/10.0, event_count/100.0, 0.5])

        if len(time_series_data) < self.look_back + 5: return 0
        
        dataset = np.array(time_series_data)
        dataset_scaled = self.scaler.fit_transform(dataset)
        
        # 2. Tạo cửa sổ trượt (Sliding Window)
        X, y = [], []
        for i in range(self.look_back, len(dataset_scaled)):
            X.append(dataset_scaled[i-self.look_back:i, :]) 
            y.append(dataset_scaled[i, 2]) # Dự đoán MaxMag (index 2)
            
        X, y = np.array(X), np.array(y)
        
        # 3. Huấn luyện
        self.model.fit(X, y, epochs=5, batch_size=1, verbose=0)
        self.is_trained = True
        
        return len(X)

    def learn(self, sensors_data):
        """Hàm Wrapper để tương thích với API cũ"""
        return self.train_from_memory()

    def predict_risk(self, lat, lon, energy, anomaly):
        if not self.is_trained:
            # Fallback (Chế độ chờ)
            return (energy * 0.6) + (anomaly * 0.4)
            
        try:
            # Giả lập input (Vì chưa có cơ chế query history realtime cho từng request)
            current_features = [energy, anomaly, energy, 0.5, 0.5]
            
            # Nhân bản input hiện tại thành chuỗi (cho demo)
            input_seq = np.array([current_features] * self.look_back)
            input_seq = self.scaler.transform(input_seq)
            
            input_reshaped = np.reshape(input_seq, (1, self.look_back, 5))
            
            prediction = self.model.predict(input_reshaped, verbose=0)
            return float(prediction[0][0])
            
        except Exception as e:
            print(f"LSTM Error: {e}")
            return 0.5

# Singleton Instance
guardian_brain = DeepGuardian()