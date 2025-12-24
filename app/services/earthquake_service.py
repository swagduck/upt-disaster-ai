import httpx
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime, timezone

# --- [IMPORTS CORE] ---
from app.core.database import Database

# --- [IMPORTS ENGINE - LIÊN KẾT VẬT LÝ] ---
from app.upt_engine.reactor_core import upt_reactor
from app.upt_engine.formulas import UPTMath
from app.upt_engine.deep_core import guardian_brain

load_dotenv()

class DisasterService:
    
    # API ENDPOINTS
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    NASA_EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30"
    
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
        
        # Biến theo dõi tổng năng lượng vũ trụ (Solar X-Ray Flux)
        total_cosmic_energy = 0.0

        async with httpx.AsyncClient() as client:
            try:
                # Tăng timeout để đảm bảo fetch được hết các nguồn
                resp_usgs, resp_nasa, resp_solar = await asyncio.gather(
                    client.get(DisasterService.USGS_URL, timeout=30.0),
                    client.get(DisasterService.NASA_EONET, timeout=30.0),
                    client.get(DisasterService.NASA_SOLAR, timeout=20.0),
                    return_exceptions=True
                )

                # 1. XỬ LÝ USGS (ĐỘNG ĐẤT)
                if isinstance(resp_usgs, httpx.Response) and resp_usgs.status_code == 200:
                    features = resp_usgs.json().get('features', [])
                    
                    for q in features:
                        props = q['properties']
                        mag = props.get('mag', 0) or 0
                        
                        if mag < 1.0: continue 
                        
                        place = props['place']
                        # Energy chuẩn hóa (0.0 - 1.0)
                        energy = min(max(mag / 9.0, 0.0), 1.0)
                        
                        # Cảnh báo Telegram (> 6.0)
                        if mag >= 6.0:
                            msg = f"🚨 [EARTHQUAKE] Động đất lớn!\nVị trí: {place}\nCường độ: {mag} Richter"
                            if place not in DisasterService.alerted_events:
                                DisasterService.alerted_events.add(place)
                                new_alerts.append(msg)
                                
                                # Gây sốc vật lý tức thì cho lò phản ứng
                                print(f"⚠️ TRIGGERING REACTOR SHOCK: {place}")
                                upt_reactor.update_external_stress(energy)

                        sensors.append({
                            "type": "EARTHQUAKE", "place": place,
                            "lat": q['geometry']['coordinates'][1], "lon": q['geometry']['coordinates'][0],
                            "energy_level": energy, "anomaly_score": props.get('sig',0)/1000.0,
                            "raw_val": mag
                        })

                # 2. XỬ LÝ NASA EONET (THIÊN TAI BỀ MẶT)
                if isinstance(resp_nasa, httpx.Response) and resp_nasa.status_code == 200:
                    events = resp_nasa.json().get('events', [])
                    for ev in events[:500]: 
                        if not ev.get('geometry'): continue
                        cat = ev['categories'][0]['id']
                        geo_raw = ev['geometry'][0]['coordinates']
                        
                        # Xử lý tọa độ phức tạp (Point vs Polygon)
                        lon, lat = 0, 0
                        if isinstance(geo_raw[0], list): # Polygon
                            lon, lat = geo_raw[0][0], geo_raw[0][1]
                        else: # Point
                            lon, lat = geo_raw[0], geo_raw[1]
                        
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
                                "lat": lat, "lon": lon,
                                "energy_level": energy, "anomaly_score": 0.6,
                                "raw_val": 5.0
                            })

                # 3. XỬ LÝ NASA SOLAR (VẬT LÝ THIÊN VĂN)
                if isinstance(resp_solar, httpx.Response) and resp_solar.status_code == 200:
                    flares = resp_solar.json()
                    if flares and isinstance(flares, list):
                        # Lấy 3 sự kiện lóa mặt trời mới nhất
                        latest_flares = sorted(flares, key=lambda x: x.get('beginTime', ''), reverse=True)[:3]
                        
                        for flare in latest_flares:
                            class_type = flare.get('classType', 'B')
                            # Chuyển đổi Class thành Energy (Logarithmic Scale)
                            energy = 0.1
                            if 'C' in class_type: energy = 0.3
                            if 'M' in class_type: energy = 0.6
                            if 'X' in class_type: energy = 1.0 # Cực đại
                            
                            # Cập nhật tổng năng lượng vũ trụ
                            total_cosmic_energy = max(total_cosmic_energy, energy)
                            
                            sensors.append({
                                "type": "SOLAR_FLARE", 
                                "place": f"Sunspot {flare.get('activeRegionNum', 'Unknown')} ({class_type})",
                                "lat": 90.0, "lon": 0.0, # Điểm tác động cực từ
                                "energy_level": energy, "anomaly_score": 0.99,
                                "raw_val": energy * 10
                            })

            except Exception as e:
                print(f"Error fetching data: {e}")

        # --- [LEVEL 4 LOGIC] KÍCH HOẠT LIÊN KẾT VŨ TRỤ (COSMIC COUPLING) ---
        if total_cosmic_energy > 0:
            # Tính toán hệ số tác động dựa trên công thức UPT
            coupling_factor = UPTMath.calculate_geomagnetic_coupling(total_cosmic_energy)
            
            # Tiêm vào lò phản ứng (Gây nhiễu từ trường tồn dư)
            if coupling_factor > 0.1:
                upt_reactor.inject_cosmic_interference(coupling_factor)
                
                # Cảnh báo Telegram nếu tác động lớn
                if coupling_factor > 0.4:
                    msg = f"⚠️ [COSMIC ALERT] Phát hiện Bão từ mạnh!\nHệ số liên kết: {coupling_factor:.3f}\nLò phản ứng đang chịu nhiễu loạn pha."
                    if "COSMIC_STORM" not in DisasterService.alerted_events:
                         DisasterService.alerted_events.add("COSMIC_STORM")
                         new_alerts.append(msg)
        # -------------------------------------------------------------------

        for msg in new_alerts:
            await DisasterService.send_telegram_alert(msg)

        if sensors:
            DisasterService.LATEST_DATA = sensors
            print(f"✅ [CACHE] Updated {len(sensors)} REAL events from global sensors.")
            
            # --- [AI FEED] NẠP DỮ LIỆU THẬT VÀO NÃO AI ---
            guardian_brain.update_realtime_state(sensors)
            # ---------------------------------------------
            
            # Lưu Snapshot vào MongoDB
            try:
                collection = Database.get_collection("raw_logs")
                if collection is not None:
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc),
                        "total_events": len(sensors),
                        "max_magnitude": max([s['raw_val'] for s in sensors]) if sensors else 0,
                        "sensors_data": sensors 
                    }
                    collection.insert_one(log_entry)
            except Exception as e:
                print(f"⚠️ [DB SAVE ERROR] Could not save to MongoDB: {e}")
            
        return sensors

    @staticmethod
    def get_latest_data():
        return DisasterService.LATEST_DATA