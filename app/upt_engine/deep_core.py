import numpy as np
import tensorflow as tf
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import DBSCAN
from collections import deque
import logging
from global_land_mask import globe

from app.core.database import Database
from app.core.logger import get_logger

logger = get_logger(__name__)

class DeepGuardian:
    def __init__(self):
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        self.look_back = 20  # Time steps for LSTM (temporal)
        self.num_features = 5
        
        self.spatial_look_back = 10
        self.spatial_features = 4 # lat, lon, mag, depth
        
        self.is_trained = False
        self.metrics = {"mse": 0.0, "mae": 0.0, "tolerance_accuracy": 0.0}
        
        self.model = self._build_model()
        
        self.hazard_types = ["EARTHQUAKE", "STORM", "WILDFIRE"]
        self.hazard_models = {ht: self._build_spatial_model() for ht in self.hazard_types}
        self.hazard_buffers = {ht: deque(maxlen=self.spatial_look_back) for ht in self.hazard_types}
        
        self.dynamic_hotspots = []
        
        self.realtime_buffer = deque(maxlen=self.look_back)

    def _build_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(64, input_shape=(self.look_back, self.num_features), return_sequences=False),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(1, activation='sigmoid')  # Output risk score between 0 and 1
        ])
        model.compile(optimizer='adam', loss='mse', metrics=['mae'])
        return model

    def _build_spatial_model(self):
        model = tf.keras.Sequential([
            tf.keras.layers.LSTM(32, input_shape=(self.spatial_look_back, self.spatial_features), return_sequences=False),
            tf.keras.layers.Dense(16, activation='relu'),
            tf.keras.layers.Dense(4, activation='sigmoid')  # Output normalized lat, lon, mag, depth
        ])
        model.compile(optimizer='adam', loss='mse')
        return model

    def initialize(self):
        """Initialize AI and train from MongoDB."""
        logger.info("[DEEP CORE] 🧠 DeepGuardian (Multi-Hazard LSTM) initialized. Connecting to memory...")
        try:
            if Database.db is not None:
                self.train_from_memory()
        except Exception as e:
            logger.error(f"[DEEP CORE] Initialization error: {e}", exc_info=True)

    def _extract_features(self, sensors):
        if not sensors:
            return [0, 0, 0, 0, 0]

        avg_energy = np.mean([s.get("energy_level", 0) for s in sensors])
        avg_anomaly = np.mean([s.get("anomaly_score", 0) for s in sensors])
        
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

    def _normalize_spatial(self, lat, lon, mag, depth=10.0):
        return [(lat + 90.0) / 180.0, (lon + 180.0) / 360.0, mag / 10.0, max(min(depth / 700.0, 1.0), 0.0)]

    def _denormalize_spatial(self, n_lat, n_lon, n_mag, n_depth=0.0):
        return (n_lat * 180.0) - 90.0, (n_lon * 360.0) - 180.0, n_mag * 10.0, n_depth * 700.0

    def _detect_hotspots(self, logs):
        """Sử dụng DBSCAN để tự động quét ra Top 5 Cụm đứt gãy hoạt động mạnh nhất."""
        try:
            coords = []
            for log in logs:
                for s in log.get("sensors_data", []):
                    if s.get("type") == "EARTHQUAKE" and s.get("raw_val", 0) > 1.5:
                        lat, lon = s.get("lat"), s.get("lon")
                        if lat is not None and lon is not None:
                            coords.append([lon, lat])
            
            if len(coords) < 100:
                return []
                
            coords_arr = np.array(coords)
            dbscan = DBSCAN(eps=3.5, min_samples=15)
            labels = dbscan.fit_predict(coords_arr)
            
            from collections import defaultdict
            clusters = defaultdict(list)
            for i, lbl in enumerate(labels):
                if lbl != -1:
                    clusters[lbl].append(coords_arr[i])
                    
            sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)[:5]
            
            hotspots = []
            for lbl, pts in sorted_clusters:
                pts_arr = np.array(pts)
                avg_lon = np.mean(pts_arr[:, 0])
                avg_lat = np.mean(pts_arr[:, 1])
                hotspots.append({
                    "name": f"Dynamic Hotspot (Cluster {lbl})",
                    "lat": float(avg_lat),
                    "lon": float(avg_lon),
                    "base_risk": min(0.30, 0.15 + (len(pts) / 5000.0))
                })
                
            logger.info(f"[DEEP CORE] 🗺️ Detected {len(hotspots)} dynamic hotspots via DBSCAN.")
            self.dynamic_hotspots = hotspots
            return hotspots
        except Exception as e:
            logger.error(f"[DEEP CORE] DBSCAN Hotspot detection failed: {e}", exc_info=True)
            return []

    def train_from_memory(self):
        col = Database.get_collection("raw_logs")
        if col is None:
            return 0

        try:
            logs = list(col.find().sort("timestamp", -1).limit(3000))
            logs.reverse() # chronologically ascending
        except Exception as e:
            logger.error(f"[DEEP CORE] Failed to read training data from DB: {e}")
            return 0
            
        # Tích hợp quét Hotspots
        self._detect_hotspots(logs)

        if len(logs) < self.look_back + 10:
            logger.warning(
                f"[DEEP CORE] Insufficient DB records ({len(logs)}) "
                f"— minimum {self.look_back + 10} required for training."
            )
            return 0

        data = []
        # Tách riêng các chuỗi không gian cho từng thảm họa
        all_hazards = {ht: [] for ht in self.hazard_types}
        
        for log in logs:
            sensors = log.get("sensors_data", [])
            features = self._extract_features(sensors)
            data.append(features)
            
            for s in sensors:
                htype = s.get("type")
                if htype in self.hazard_types and s.get("raw_val", 0) > 0:
                    all_hazards[htype].append(self._normalize_spatial(s.get("lat", 0), s.get("lon", 0), s.get("raw_val", 0), s.get("depth", 10.0)))

        # Temporal Model
        dataset = np.array(data)
        split_idx = int(len(dataset) * 0.8)
        if split_idx > 0:
            self.scaler.fit(dataset[:split_idx])
        else:
            self.scaler.fit(dataset)
            
        dataset_scaled = self.scaler.transform(dataset)

        X_temp, y_temp = [], []
        forecast_horizon = 5 
        for i in range(self.look_back, len(dataset_scaled) - forecast_horizon):
            window = dataset_scaled[i - self.look_back: i, :]
            X_temp.append(window)
            target_risk = (dataset_scaled[i + forecast_horizon, 1] + dataset_scaled[i + forecast_horizon, 2]) / 2.0
            y_temp.append(target_risk)

        X_temp = np.array(X_temp)
        y_temp = np.array(y_temp)

        if len(X_temp) > 0:
            logger.info(f"[DEEP CORE] Training Temporal LSTM on {len(X_temp)} samples...")
            self.model.fit(X_temp, y_temp, epochs=10, batch_size=32, verbose=0)
            self.evaluate_accuracy(X_temp, y_temp)

        # Spatial Models
        for ht in self.hazard_types:
            h_data = all_hazards[ht]
            if len(h_data) > self.spatial_look_back + 5:
                X_spatial, y_spatial = [], []
                for i in range(self.spatial_look_back, len(h_data) - 1):
                    X_spatial.append(h_data[i - self.spatial_look_back : i])
                    y_spatial.append(h_data[i])
                
                logger.info(f"[DEEP CORE] Training Spatial LSTM ({ht}) on {len(X_spatial)} sequences...")
                self.hazard_models[ht].fit(np.array(X_spatial), np.array(y_spatial), epochs=10, batch_size=32, verbose=0)
                
                # Populate buffers
                for eq in h_data[-self.spatial_look_back:]:
                    self.hazard_buffers[ht].append(eq)

        self.is_trained = True
        return len(X_temp)

    def evaluate_accuracy(self, X, y):
        if len(X) == 0:
            return
        try:
            preds = self.model.predict(X, verbose=0).flatten()
            mse = np.mean((y - preds) ** 2)
            mae = np.mean(np.abs(y - preds))
            tolerance_accuracy = max(0.0, (1.0 - mae)) * 100
            
            self.metrics = {
                "mse": round(float(mse), 4),
                "mae": round(float(mae), 4),
                "tolerance_accuracy": round(float(tolerance_accuracy), 2)
            }
            logger.info(f"[DEEP CORE] Temporal LSTM Accuracy: {self.metrics['tolerance_accuracy']}% (MSE={self.metrics['mse']})")
        except Exception as e:
            logger.error(f"[DEEP CORE] Evaluation failed: {e}", exc_info=True)

    def update_realtime_state(self, sensors):
        features = self._extract_features(sensors)
        self.realtime_buffer.append(features)
        
        for s in sensors:
            htype = s.get("type")
            if htype in self.hazard_types and s.get("raw_val", 0) > 0:
                self.hazard_buffers[htype].append(self._normalize_spatial(s.get("lat", 0), s.get("lon", 0), s.get("raw_val", 0), s.get("depth", 10.0)))
                
    def learn(self, sensors):
        self.update_realtime_state(sensors)
        
        data = []
        all_hazards = {ht: [] for ht in self.hazard_types}
        sensors_chronological = list(reversed(sensors))
        
        for s in sensors_chronological:
            data.append(self._extract_features([s]))
            htype = s.get("type")
            if htype in self.hazard_types and s.get("raw_val", 0) > 0:
                all_hazards[htype].append(self._normalize_spatial(s.get("lat", 0), s.get("lon", 0), s.get("raw_val", 0), s.get("depth", 10.0)))
                
        dataset = np.array(data)
        
        # Temporal Model
        if len(dataset) > self.look_back + 5:
            self.scaler.fit(dataset)
            dataset_scaled = self.scaler.transform(dataset)
            X_temp, y_temp = [], []
            forecast_horizon = 2
            for i in range(self.look_back, len(dataset_scaled) - forecast_horizon):
                window = dataset_scaled[i - self.look_back: i, :]
                X_temp.append(window)
                target_risk = (dataset_scaled[i + forecast_horizon, 1] + dataset_scaled[i + forecast_horizon, 2]) / 2.0
                y_temp.append(target_risk)
                
            if len(X_temp) > 0:
                logger.info(f"[DEEP CORE] Online Learning: Training Temporal LSTM on {len(X_temp)} live samples...")
                self.model.fit(np.array(X_temp), np.array(y_temp), epochs=10, batch_size=16, verbose=0)
                
        # Spatial Models
        for ht in self.hazard_types:
            h_data = all_hazards[ht]
            if len(h_data) > self.spatial_look_back + 3:
                X_spatial, y_spatial = [], []
                for i in range(self.spatial_look_back, len(h_data) - 1):
                    X_spatial.append(h_data[i - self.spatial_look_back : i])
                    y_spatial.append(h_data[i])
                    
                if len(X_spatial) > 0:
                    logger.info(f"[DEEP CORE] Online Learning: Training Spatial LSTM ({ht}) on {len(X_spatial)} sequences...")
                    self.hazard_models[ht].fit(np.array(X_spatial), np.array(y_spatial), epochs=15, batch_size=8, verbose=0)

        # Trạng thái is_trained
        # Nếu ít nhất 1 buffer đủ dữ liệu thì xem như được học (đủ để dự đoán)
        if any(len(self.hazard_buffers[ht]) >= self.spatial_look_back for ht in self.hazard_types):
            self.is_trained = True
            
        return len(sensors)

    def predict_risk(self, lat, lon, local_energy, local_anomaly):
        if len(self.realtime_buffer) < self.look_back:
            return min(local_energy * 0.6 + local_anomaly * 0.4, 1.0)

        if not self.is_trained:
            return (local_energy + local_anomaly) / 2.0

        try:
            raw_seq = np.array(list(self.realtime_buffer))
            seq_scaled = self.scaler.transform(raw_seq)
            input_shaped = seq_scaled.reshape(1, self.look_back, self.num_features)
            
            global_instability = float(self.model.predict(input_shaped, verbose=0)[0][0])

            location_factor = (local_energy * 0.6) + (local_anomaly * 0.4)
            final_risk = (global_instability * 0.4) + (location_factor * 0.6)

            return min(max(final_risk, 0.0), 1.0)

        except Exception as e:
            logger.error(f"[DEEP CORE] Temporal LSTM prediction failed: {e}", exc_info=True)
            return 0.5
            
    def _find_nearest_land(self, lat, lon, max_radius_deg=5.0, step=0.5):
        """Spiral search for nearest land coordinate."""
        radius = step
        while radius <= max_radius_deg:
            for angle in range(0, 360, 45):
                rad = np.radians(angle)
                test_lat = lat + radius * np.cos(rad)
                test_lon = lon + radius * np.sin(rad)
                # Keep within bounds
                test_lat = max(min(test_lat, 90.0), -90.0)
                test_lon = max(min(test_lon, 180.0), -180.0)
                if globe.is_land(test_lat, test_lon):
                    return test_lat, test_lon
            radius += step
        return None, None

    def predict_next_hazards(self):
        """Predict the next disaster coordinates for each supported hazard type."""
        predictions = []
        if not self.is_trained:
            return predictions
            
        for ht in self.hazard_types:
            buffer = self.hazard_buffers[ht]
            if len(buffer) < self.spatial_look_back:
                continue
                
            try:
                seq = np.array(list(buffer))
                input_shaped = seq.reshape(1, self.spatial_look_back, self.spatial_features)
                pred_norm = self.hazard_models[ht].predict(input_shaped, verbose=0)[0]
                lat, lon, mag, depth = self._denormalize_spatial(pred_norm[0], pred_norm[1], pred_norm[2], pred_norm[3] if len(pred_norm) > 3 else 0.0)
                
                lat = max(min(lat, 90.0), -90.0)
                lon = max(min(lon, 180.0), -180.0)
                
                # TOPOGRAPHICAL FILTER
                if ht == "WILDFIRE":
                    if not globe.is_land(lat, lon):
                        logger.warning(f"[DEEP CORE] Topographical Filter: Wildfire predicted in ocean at ({lat}, {lon}). Scanning for land...")
                        new_lat, new_lon = self._find_nearest_land(lat, lon)
                        if new_lat is not None:
                            logger.info(f"[DEEP CORE] Shifted Wildfire prediction to nearest land: ({new_lat}, {new_lon})")
                            lat, lon = new_lat, new_lon
                        else:
                            logger.warning("[DEEP CORE] No land found within radius. Dropping Wildfire prediction.")
                            continue # Drop prediction if no land found
                
                predictions.append({
                    "type": ht,
                    "lat": round(float(lat), 3), 
                    "lon": round(float(lon), 3), 
                    "mag": round(float(mag), 1),
                    "depth": round(float(depth), 1)
                })
                
            except Exception as e:
                logger.error(f"[DEEP CORE] Spatial LSTM prediction failed for {ht}: {e}", exc_info=True)
                
        return predictions

guardian_brain = DeepGuardian()