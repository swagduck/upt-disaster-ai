import requests

class USGSService:
    """
    Kết nối với Cục Khảo sát Địa chất Hoa Kỳ (USGS)
    Lấy dữ liệu động đất trong 1 giờ qua.
    """
    
    BASE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"

    @staticmethod
    def fetch_live_data():
        try:
            response = requests.get(USGSService.BASE_URL)
            if response.status_code == 200:
                data = response.json()
                features = data.get('features', [])
                
                # Chuyển đổi dữ liệu USGS sang tham số UPT
                sensors = []
                for quake in features[:5]: # Lấy 5 trận động đất mới nhất
                    props = quake['properties']
                    geometry = quake['geometry']
                    
                    # Mapping logic UPT:
                    # Magnitude (Độ lớn) -> Energy (E) (Chuẩn hóa: chia cho 10)
                    mag = props.get('mag', 0) or 0
                    energy_e = min(max(mag / 10.0, 0.0), 1.0) 
                    
                    # Sig (Độ quan trọng) -> Anomaly (A) (Chuẩn hóa: chia cho 1000)
                    sig = props.get('sig', 0) or 0
                    anomaly_a = min(max(sig / 1000.0, 0.0), 1.0)

                    sensors.append({
                        "station_id": f"USGS-{quake['id']}",
                        "energy_level": energy_e,
                        "anomaly_score": anomaly_a,
                        "location_weight": 1.0,
                        # Lưu thêm tọa độ để vẽ lên bản đồ sau này
                        "lat": geometry['coordinates'][1],
                        "lon": geometry['coordinates'][0],
                        "place": props['place']
                    })
                
                return sensors
            return []
        except Exception as e:
            print(f"Lỗi kết nối USGS: {e}")
            return []