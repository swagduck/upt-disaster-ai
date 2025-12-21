import requests

class DisasterService:
    """
    CORE SERVICE V2:
    Kết hợp dữ liệu từ:
    1. USGS (United States Geological Survey) - Động đất
    2. NASA EONET (Earth Observatory Natural Event Tracker) - Bão, Cháy rừng, Núi lửa
    """
    
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    NASA_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=10"

    @staticmethod
    def fetch_all_realtime():
        sensors = []
        
        # --- NGUỒN 1: ĐỘNG ĐẤT (USGS) ---
        try:
            resp_quake = requests.get(DisasterService.USGS_URL, timeout=5)
            if resp_quake.status_code == 200:
                features = resp_quake.json().get('features', [])
                for q in features[:10]: # Lấy 10 trận mới nhất
                    mag = q['properties'].get('mag', 0) or 0
                    # Logic UPT: Động đất > 6.0 là nguy hiểm cao
                    energy = min(max(mag / 8.0, 0.0), 1.0) 
                    
                    sensors.append({
                        "type": "EARTHQUAKE",
                        "place": q['properties']['place'],
                        "lat": q['geometry']['coordinates'][1],
                        "lon": q['geometry']['coordinates'][0],
                        "energy_level": energy,
                        "anomaly_score": min(max((q['properties'].get('sig',0) or 0)/1000.0, 0.0), 1.0)
                    })
        except Exception as e:
            print(f"Lỗi kết nối USGS: {e}")

        # --- NGUỒN 2: THIÊN TAI KHÁC (NASA) ---
        try:
            resp_nasa = requests.get(DisasterService.NASA_URL, timeout=5)
            if resp_nasa.status_code == 200:
                events = resp_nasa.json().get('events', [])
                for ev in events[:15]: # Lấy 15 sự kiện mới nhất
                    if not ev.get('geometry'): continue
                    
                    cat_id = ev['categories'][0]['id']
                    geo = ev['geometry'][0]['coordinates'] # NASA trả về [lon, lat]
                    
                    # Mapping logic UPT cho từng loại thiên tai
                    disaster_type = "UNKNOWN"
                    energy = 0.5
                    anomaly = 0.5

                    if cat_id == 'wildfires': 
                        disaster_type = "WILDFIRE"
                        energy = 0.75 
                        anomaly = 0.6
                    elif cat_id == 'volcanoes':
                        disaster_type = "VOLCANO"
                        energy = 0.95 
                        anomaly = 0.85
                    elif cat_id == 'severeStorms':
                        disaster_type = "STORM"
                        energy = 0.88
                        anomaly = 0.7
                    elif cat_id == 'seaLakeIce':
                        disaster_type = "ICEBERG"
                        energy = 0.4
                        anomaly = 0.9
                    
                    sensors.append({
                        "type": disaster_type,
                        "place": ev['title'],
                        "lat": geo[1],
                        "lon": geo[0],
                        "energy_level": energy,
                        "anomaly_score": anomaly
                    })
        except Exception as e:
            print(f"Lỗi kết nối NASA: {e}")

        return sensors