import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import os

class GuardianAI:
    def __init__(self):
        self.model_path = "app/upt_engine/guardian_model.pkl"
        self.scaler = StandardScaler()
        # Sử dụng Random Forest: Mạnh mẽ, chống overfitting tốt cho dữ liệu thảm họa
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.is_trained = False
        
        # Dữ liệu mẫu khởi tạo (Seed Data) để AI không bị lỗi khi chưa có dữ liệu thật
        # Feature: [Lat, Lon, Energy, Anomaly]
        self.X_buffer = [
            [35.0, 139.0, 0.8, 0.5],  # Japan Quake (Mẫu)
            [-5.0, 120.0, 0.6, 0.7],  # Indonesia Volcano (Mẫu)
            [37.0, -122.0, 0.4, 0.2], # USA Minor (Mẫu)
            [15.0, 108.0, 0.2, 0.1],  # Vietnam Minor (Mẫu)
        ]
        # Label: [Risk_Score] (0.0 -> 1.0)
        self.y_buffer = [0.9, 0.7, 0.3, 0.1] 
        
        self._initial_train()

    def _initial_train(self):
        """Huấn luyện sơ bộ khi khởi động server"""
        try:
            X = np.array(self.X_buffer)
            y = np.array(self.y_buffer)
            self.scaler.fit(X)
            self.model.fit(self.scaler.transform(X), y)
            self.is_trained = True
            print("🧠 [NEURAL CORE] AI Model initialized and active.")
        except Exception as e:
            print(f"⚠️ [NEURAL CORE] Init failed: {e}")

    def learn(self, sensors_data):
        """Học từ dữ liệu thời gian thực mới nhất (Online Learning)"""
        new_events = 0
        for s in sensors_data:
            # Chỉ học từ các sự kiện có cấu trúc hợp lệ từ DisasterService
            # Cần đảm bảo s là dict và có các key cần thiết
            if isinstance(s, dict) and 'lat' in s and 'lon' in s:
                energy = s.get('energy_level', 0.5)
                anomaly = s.get('anomaly_score', 0.5)
                
                feature = [s['lat'], s['lon'], energy, anomaly]
                
                # Giả định Risk = Energy * 0.7 + Anomaly * 0.3 (Heuristic Labeling)
                # Trong thực tế, label này nên đến từ dữ liệu thiệt hại lịch sử
                label = min(1.0, energy * 0.7 + anomaly * 0.3)
                
                self.X_buffer.append(feature)
                self.y_buffer.append(label)
                new_events += 1
        
        # Giới hạn bộ nhớ đệm (Rolling Window) để tránh tràn RAM
        max_buffer = 2000
        if len(self.X_buffer) > max_buffer:
            self.X_buffer = self.X_buffer[-max_buffer:]
            self.y_buffer = self.y_buffer[-max_buffer:]
            
        # Retrain nhanh
        if new_events > 0:
            X = np.array(self.X_buffer)
            y = np.array(self.y_buffer)
            self.model.fit(self.scaler.transform(X), y)
            
        return len(self.X_buffer)

    def predict_risk(self, lat, lon, energy, anomaly):
        """Dự đoán rủi ro cho một tọa độ bất kỳ"""
        if not self.is_trained: return 0.0
        
        try:
            input_data = np.array([[lat, lon, energy, anomaly]])
            scaled_input = self.scaler.transform(input_data)
            prediction = self.model.predict(scaled_input)[0]
            return float(max(0.0, min(1.0, prediction)))
        except Exception as e:
            print(f"Prediction Error: {e}")
            return 0.0

# Singleton Instance (Dùng chung cho cả App)
guardian_brain = GuardianAI()