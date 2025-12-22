import requests
import asyncio
from telegram import Bot

class DisasterService:
    
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
    NASA_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=10"
    
    # --- CẤU HÌNH TELEGRAM (QUAN TRỌNG) ---
    
    # 1. Điền Token bạn lấy từ BotFather vào giữa 2 dấu nháy:
    TELEGRAM_TOKEN = "THAY_TOKEN_CUA_BAN_VAO_DAY" 
    
    # 2. ID của bạn (Tôi đã điền sẵn):
    CHAT_ID = "8322247844"
    
    # ---------------------------------------
    
    # Khởi tạo Bot
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
    except:
        bot = None
    
    alerted_events = set()

    @staticmethod
    async def send_telegram_alert(message):
        """Gửi tin nhắn cảnh báo qua Telegram"""
        if not DisasterService.bot: return
        try:
            await DisasterService.bot.send_message(
                chat_id=DisasterService.CHAT_ID, 
                text=message
            )
        except Exception as e:
            print(f"Lỗi Telegram: {e}")

    @staticmethod
    async def fetch_all_realtime():
        sensors = []
        new_critical_events = []

        # --- 1. LẤY DỮ LIỆU ĐỘNG ĐẤT (USGS) ---
        try:
            resp = requests.get(DisasterService.USGS_URL, timeout=5)
            if resp.status_code == 200:
                features = resp.json().get('features', [])
                for q in features[:10]:
                    props = q['properties']
                    place = props['place']
                    mag = props.get('mag', 0) or 0
                    energy = min(max(mag / 9.0, 0.0), 1.0)
                    
                    # CẢNH BÁO: Nếu động đất > 6.0 độ (Energy > 0.65)
                    if energy > 0.65 and place not in DisasterService.alerted_events:
                        DisasterService.alerted_events.add(place)
                        msg = f"⚠️ [CRITICAL ALERT]\nLoại: ĐỘNG ĐẤT 📉\nVị trí: {place}\nĐộ lớn: {mag} Richter\nNăng lượng UPT: {energy:.2f}"
                        new_critical_events.append(msg)

                    sensors.append({
                        "type": "EARTHQUAKE", "place": place,
                        "lat": q['geometry']['coordinates'][1], "lon": q['geometry']['coordinates'][0],
                        "energy_level": energy,
                        "anomaly_score": min(max((props.get('sig',0) or 0)/1000.0, 0.0), 1.0)
                    })
        except Exception: pass

        # --- 2. LẤY DỮ LIỆU THIÊN TAI (NASA) ---
        try:
            resp = requests.get(DisasterService.NASA_URL, timeout=5)
            if resp.status_code == 200:
                events = resp.json().get('events', [])
                for ev in events[:15]:
                    if not ev.get('geometry'): continue
                    title = ev['title']
                    cat = ev['categories'][0]['id']
                    geo = ev['geometry'][0]['coordinates']
                    
                    type_map = {
                        'wildfires': ("WILDFIRE", 0.75, "🔥"),
                        'volcanoes': ("VOLCANO", 0.95, "🌋"),
                        'severeStorms': ("STORM", 0.88, "🌀"),
                        'seaLakeIce': ("ICEBERG", 0.4, "❄️")
                    }
                    
                    if cat in type_map:
                        d_type, energy, icon = type_map[cat]
                        
                        # CẢNH BÁO: Nếu năng lượng NASA > 0.8 (Bão lớn/Núi lửa)
                        if energy > 0.8 and title not in DisasterService.alerted_events:
                            DisasterService.alerted_events.add(title)
                            msg = f"⚠️ [CRITICAL ALERT]\nLoại: {d_type} {icon}\nVị trí: {title}\nNăng lượng UPT: {energy}"
                            new_critical_events.append(msg)

                        sensors.append({
                            "type": d_type, "place": title,
                            "lat": geo[1], "lon": geo[0],
                            "energy_level": energy, "anomaly_score": 0.7
                        })
        except Exception: pass
        
        # Gửi tin nhắn đồng loạt
        for msg in new_critical_events:
            await DisasterService.send_telegram_alert(msg)

        return sensors