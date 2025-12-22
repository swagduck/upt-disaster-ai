import httpx
import asyncio
from telegram import Bot

class DisasterService:
    
    # API ENDPOINTS
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    NASA_EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=10"
    NASA_SOLAR = "https://api.nasa.gov/DONKI/FLR?startDate=2024-01-01&api_key=DEMO_KEY" # Bão mặt trời

    # --- CONFIG TELEGRAM ---
    TELEGRAM_TOKEN = "THAY_TOKEN_CUA_BAN_VAO_DAY" 
    CHAT_ID = "8322247844"
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except:
        bot = None
    
    alerted_events = set()

    @staticmethod
    async def send_telegram_alert(message):
        if not DisasterService.bot: return
        try:
            await DisasterService.bot.send_message(chat_id=DisasterService.CHAT_ID, text=message)
        except: pass

    @staticmethod
    async def fetch_all_realtime():
        sensors = []
        new_alerts = []

        # SỬ DỤNG HTTPX ĐỂ GỌI SONG SONG (SIÊU TỐC ĐỘ)
        async with httpx.AsyncClient() as client:
            try:
                # Gọi 3 API cùng 1 lúc, không chờ nhau
                resp_usgs, resp_nasa, resp_solar = await asyncio.gather(
                    client.get(DisasterService.USGS_URL, timeout=4.0),
                    client.get(DisasterService.NASA_EONET, timeout=4.0),
                    client.get(DisasterService.NASA_SOLAR, timeout=4.0),
                    return_exceptions=True # Lỗi 1 cái thì mấy cái kia vẫn chạy
                )

                # --- 1. XỬ LÝ USGS (ĐỘNG ĐẤT + SÓNG THẦN) ---
                if isinstance(resp_usgs, httpx.Response) and resp_usgs.status_code == 200:
                    features = resp_usgs.json().get('features', [])
                    for q in features[:10]:
                        props = q['properties']
                        mag = props.get('mag', 0) or 0
                        place = props['place']
                        tsunami = props.get('tsunami', 0) # Cờ báo sóng thần
                        
                        energy = min(max(mag / 9.0, 0.0), 1.0)
                        
                        # Logic Sóng thần
                        d_type = "EARTHQUAKE"
                        if tsunami == 1:
                            d_type = "TSUNAMI"
                            energy = 1.0 # Sóng thần auto max năng lượng
                            msg = f"🌊 [TSUNAMI WARNING]\nVị trí: {place}\nDo động đất: {mag} độ"
                            if place not in DisasterService.alerted_events:
                                DisasterService.alerted_events.add(place)
                                new_alerts.append(msg)

                        sensors.append({
                            "type": d_type, "place": place,
                            "lat": q['geometry']['coordinates'][1], "lon": q['geometry']['coordinates'][0],
                            "energy_level": energy, "anomaly_score": props.get('sig',0)/1000.0
                        })

                # --- 2. XỬ LÝ NASA EONET (BÃO, LỬA, NÚI LỬA, BĂNG) ---
                if isinstance(resp_nasa, httpx.Response) and resp_nasa.status_code == 200:
                    events = resp_nasa.json().get('events', [])
                    for ev in events[:15]:
                        if not ev.get('geometry'): continue
                        cat = ev['categories'][0]['id']
                        geo = ev['geometry'][0]['coordinates']
                        
                        # Mapping
                        meta = {
                            'wildfires': ("WILDFIRE", 0.75),
                            'volcanoes': ("VOLCANO", 0.95),
                            'severeStorms': ("STORM", 0.85),
                            'seaLakeIce': ("ICEBERG", 0.4)
                        }
                        
                        if cat in meta:
                            d_type, energy = meta[cat]
                            sensors.append({
                                "type": d_type, "place": ev['title'],
                                "lat": geo[1], "lon": geo[0],
                                "energy_level": energy, "anomaly_score": 0.6
                            })

                # --- 3. XỬ LÝ NASA SOLAR (BÃO MẶT TRỜI) ---
                # API này trả về list các đợt bùng nổ mặt trời
                if isinstance(resp_solar, httpx.Response) and resp_solar.status_code == 200:
                    flares = resp_solar.json()
                    # Lấy flare mới nhất nếu có
                    if flares and isinstance(flares, list):
                        latest = flares[-1] 
                        class_type = latest.get('classType', 'B')
                        # Class X là nguy hiểm nhất
                        energy = 0.3
                        if 'M' in class_type: energy = 0.7
                        if 'X' in class_type: energy = 1.0
                        
                        # Bão mặt trời ảnh hưởng toàn cầu -> Vẽ 1 điểm tượng trưng ở Bắc Cực
                        sensors.append({
                            "type": "SOLAR_FLARE", "place": f"Solar Flare Class {class_type}",
                            "lat": 80.0, "lon": 0.0, # Điểm giả định
                            "energy_level": energy, "anomaly_score": 0.99
                        })

            except Exception as e:
                print(f"Error fetching: {e}")

        # Gửi Telegram
        for msg in new_alerts:
            await DisasterService.send_telegram_alert(msg)

        return sensors