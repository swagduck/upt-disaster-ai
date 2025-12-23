import httpx
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

class DisasterService:
    
    # API ENDPOINTS
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson" # Đổi sang 'all_day' để lấy nhiều tin hơn (24h qua)
    NASA_EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=20"
    
    _NASA_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
    NASA_SOLAR = f"https://api.nasa.gov/DONKI/FLR?startDate=2024-01-01&api_key={_NASA_KEY}"

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    bot = None
    if TELEGRAM_TOKEN:
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
        except Exception as e:
            print(f"Telegram Init Failed: {e}")
    
    alerted_events = set()
    
    # Cache Storage
    LATEST_DATA = [] 

    @staticmethod
    async def send_telegram_alert(message):
        if not DisasterService.bot or not DisasterService.CHAT_ID: return
        try:
            await DisasterService.bot.send_message(chat_id=DisasterService.CHAT_ID, text=message)
        except Exception as e:
            print(f"Failed to send Telegram: {e}")

    @staticmethod
    async def fetch_all_realtime():
        sensors = []
        new_alerts = []

        async with httpx.AsyncClient() as client:
            try:
                # Tăng timeout lên chút để tải file JSON lớn từ USGS
                resp_usgs, resp_nasa, resp_solar = await asyncio.gather(
                    client.get(DisasterService.USGS_URL, timeout=15.0),
                    client.get(DisasterService.NASA_EONET, timeout=15.0),
                    client.get(DisasterService.NASA_SOLAR, timeout=15.0),
                    return_exceptions=True
                )

                # 1. XỬ LÝ USGS
                if isinstance(resp_usgs, httpx.Response) and resp_usgs.status_code == 200:
                    features = resp_usgs.json().get('features', [])
                    
                    # [FIX] Tăng giới hạn từ 20 lên 200 sự kiện
                    # Lọc bỏ động đất quá nhỏ (< 2.0) để đỡ rác bản đồ
                    count = 0
                    for q in features:
                        if count >= 200: break # Giới hạn an toàn
                        
                        props = q['properties']
                        mag = props.get('mag', 0) or 0
                        if mag < 2.5: continue # Bỏ qua rung chấn nhỏ
                        
                        count += 1
                        place = props['place']
                        energy = min(max(mag / 9.0, 0.0), 1.0)
                        
                        # Cảnh báo Telegram (Chỉ báo cái > 6.0)
                        if mag >= 6.0:
                            msg = f"🚨 [ALERT] Động đất lớn!\nVị trí: {place}\nCường độ: {mag} Richter"
                            if place not in DisasterService.alerted_events:
                                DisasterService.alerted_events.add(place)
                                new_alerts.append(msg)
                                # Trigger Reactor
                                from app.api.v1.endpoints.reactor import reactor
                                reactor.simulate_step(entropy_input=0, ai_intervention=True, external_shock=0.8)

                        sensors.append({
                            "type": "EARTHQUAKE", "place": place,
                            "lat": q['geometry']['coordinates'][1], "lon": q['geometry']['coordinates'][0],
                            "energy_level": energy, "anomaly_score": props.get('sig',0)/1000.0,
                            "raw_val": mag
                        })

                # 2. XỬ LÝ NASA EONET
                if isinstance(resp_nasa, httpx.Response) and resp_nasa.status_code == 200:
                    events = resp_nasa.json().get('events', [])
                    
                    # [FIX] Tăng giới hạn NASA lên 50 sự kiện
                    for ev in events[:50]:
                        if not ev.get('geometry'): continue
                        cat = ev['categories'][0]['id']
                        geo = ev['geometry'][0]['coordinates']
                        
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
                                "energy_level": energy, "anomaly_score": 0.6,
                                "raw_val": 5.0
                            })

                # 3. XỬ LÝ SOLAR
                if isinstance(resp_solar, httpx.Response) and resp_solar.status_code == 200:
                    flares = resp_solar.json()
                    if flares and isinstance(flares, list):
                        latest = flares[-1] 
                        class_type = latest.get('classType', 'B')
                        energy = 0.3
                        if 'M' in class_type: energy = 0.7
                        if 'X' in class_type: energy = 1.0
                        
                        sensors.append({
                            "type": "SOLAR_FLARE", "place": f"Class {class_type}",
                            "lat": 85.0, "lon": 0.0, # Đẩy lên cực Bắc
                            "energy_level": energy, "anomaly_score": 0.99,
                            "raw_val": 10.0
                        })

            except Exception as e:
                print(f"Error fetching data: {e}")

        # Gửi cảnh báo
        for msg in new_alerts:
            await DisasterService.send_telegram_alert(msg)

        # Cập nhật Cache
        if sensors:
            DisasterService.LATEST_DATA = sensors
            print(f"✅ [CACHE] Updated {len(sensors)} events to memory.")
            
        return sensors

    @staticmethod
    def get_latest_data():
        return DisasterService.LATEST_DATA