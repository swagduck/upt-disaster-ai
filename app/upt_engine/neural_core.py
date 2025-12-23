import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from datetime import timedelta
import os
import joblib

# Import kết nối Database
from app.core.database import Database

class GuardianAI:
    def __init__(self):
        self.scaler = StandardScaler()
        # Random Forest: Mạnh mẽ, đa năng
        self.model = RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
        self.is_trained = False
        
        # Danh sách tọa độ Vành đai lửa (Kiến thức địa lý)
        self.fault_lines = [
            [36.2, 138.2], [37.7, -122.4], [-33.4, -70.6], 
            [-6.2, 106.8], [14.0, 121.0], [-41.2, 174.7], 
            [35.0, 25.0], [28.0, 84.0]
        ]
        
        # Khởi tạo buffer
        self.X_buffer = []
        self.y_buffer = []
        
        # [QUY TRÌNH KHỞI ĐỘNG THÔNG MINH]
        # 1. Thử kết nối DB và học từ lịch sử
        if Database.db is not None:
            print("⏳ [NEURAL CORE] Mining historical data from MongoDB...")
            count = self.train_from_history()
            
            if count > 10:
                print(f"🧠 [NEURAL CORE] Trained on {count} historical snapshots (Time-Travel Mode).")
            else:
                # 2. Nếu không có lịch sử, chạy chế độ chờ (Safe Mode)
                self._init_safe_mode()
        else:
            self._init_safe_mode()

    def _get_distance_to_fault(self, lat, lon):
        """Tính khoảng cách đến điểm đứt gãy gần nhất"""
        min_dist = 99999.0
        for f_lat, f_lon in self.fault_lines:
            # 1 độ ~ 111km
            dist = np.sqrt((lat - f_lat)**2 + (lon - f_lon)**2) * 111.0
            if dist < min_dist: min_dist = dist
        return min_dist

    def _init_safe_mode(self):
        """
        [SAFE MODE] Khởi tạo mô hình ở trạng thái 'rỗng' nhưng không lỗi.
        Dùng vector zero để fit Scaler.
        """
        print("⚠️ [NEURAL CORE] No history found. Running in SAFE MODE (Waiting for data).")
        # Vector 5 chiều rỗng: [Lat, Lon, Energy, Anomaly, Dist]
        self.X_buffer = [[0.0, 0.0, 0.0, 0.0, 0.0]]
        self.y_buffer = [0.0]
        
        self.scaler.fit(self.X_buffer)
        self.model.fit(self.scaler.transform(self.X_buffer), self.y_buffer)
        self.is_trained = False 

    def train_from_history(self):
        """
        Học từ quá khứ: Input(T) -> Output(T+24h)
        """
        col = Database.get_collection("raw_logs")
        
        # Kiểm tra collection tồn tại an toàn
        if col is None: return 0
        
        try:
            # Lấy 1000 bản ghi gần nhất
            logs = list(col.find().sort("timestamp", 1).limit(1000))
        except Exception as e:
            print(f"⚠️ DB Read Error: {e}")
            return 0

        if len(logs) < 5: return 0 
        
        X_history = []
        y_history = []
        
        for i in range(len(logs)):
            current_log = logs[i]
            current_time = current_log.get('timestamp')
            if not current_time: continue

            # Tìm sự kiện lớn nhất trong 24h tới
            future_max_mag = 0.0
            found_future = False
            
            for j in range(i + 1, len(logs)):
                future_log = logs[j]
                future_time = future_log.get('timestamp')
                if not future_time: continue

                time_diff = (future_time - current_time).total_seconds()
                if time_diff > 24 * 3600: break # Chỉ nhìn xa 24h
                
                mag = future_log.get('max_magnitude', 0)
                if mag > future_max_mag:
                    future_max_mag = mag
                    found_future = True
            
            if not found_future: continue 

            sensors = current_log.get('sensors_data', [])
            if not sensors: continue
            
            # Lấy mẫu các trạm để train (Giới hạn 20 trạm/log để nhanh)
            for s in sensors[:20]: 
                if 'lat' not in s or 'lon' not in s: continue
                
                dist = self._get_distance_to_fault(s['lat'], s['lon'])
                
                X_history.append([
                    s['lat'], s['lon'], 
                    s.get('energy_level', 0), 
                    s.get('anomaly_score', 0),
                    dist
                ])
                
                # Label: Chuẩn hóa Magnitude về [0,1]
                target_risk = min(1.0, future_max_mag / 9.0)
                y_history.append(target_risk)

        if not X_history: return 0
        
        # Retrain thật
        X = np.array(X_history)
        y = np.array(y_history)
        
        self.scaler.fit(X)
        self.model.fit(self.scaler.transform(X), y)
        self.is_trained = True
        
        return len(X_history)

    def learn(self, sensors_data):
        # Level 2: Chủ yếu học từ DB (train_from_history).
        # Hàm này có thể để trống hoặc dùng để tích lũy buffer RAM tạm thời.
        return 0 
        
    def predict_risk(self, lat, lon, energy, anomaly):
        """
        Dự báo rủi ro. Nếu chưa train xong (Safe Mode) thì dùng công thức tạm.
        """
        # Fallback Logic
        if not self.is_trained:
            # Công thức cũ tạm thời
            return (energy * 0.7) + (anomaly * 0.3)
        
        try:
            dist = self._get_distance_to_fault(lat, lon)
            input_data = np.array([[lat, lon, energy, anomaly, dist]])
            scaled_input = self.scaler.transform(input_data)
            prediction = self.model.predict(scaled_input)[0]
            return float(max(0.0, min(1.0, prediction)))
        except Exception:
            return 0.0

guardian_brain = GuardianAI()