import httpx
import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from datetime import datetime, timezone

from app.core.database import Database
from app.core.config import settings
from app.core.logger import get_logger
from app.upt_engine.reactor_core import upt_reactor
from app.upt_engine.formulas import UPTMath
from app.upt_engine.deep_core import guardian_brain

load_dotenv()

logger = get_logger(__name__)


class DisasterService:

    # ── API Endpoints ────────────────────────────────────────────────────────
    USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
    NASA_EONET = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30"
    NASA_SOLAR = (
        f"https://api.nasa.gov/DONKI/FLR"
        f"?startDate=2024-01-01&api_key={settings.NASA_API_KEY}"
    )

    TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN
    CHAT_ID = settings.TELEGRAM_CHAT_ID

    bot = None
    if TELEGRAM_TOKEN:
        try:
            bot = Bot(token=TELEGRAM_TOKEN)
            logger.info("[DISASTER SVC] Telegram bot initialised successfully.")
        except Exception as e:
            logger.error(f"[DISASTER SVC] Telegram init failed: {e}")

    alerted_events: set = set()
    LATEST_DATA: list = []

    # ── Telegram ─────────────────────────────────────────────────────────────
    @staticmethod
    async def send_telegram_alert(message: str):
        if not DisasterService.bot or not DisasterService.CHAT_ID:
            return
        try:
            await DisasterService.bot.send_message(
                chat_id=DisasterService.CHAT_ID, text=message
            )
            logger.debug(f"[DISASTER SVC] Telegram alert sent: {message[:80]}...")
        except Exception as e:
            logger.error(f"[DISASTER SVC] Failed to send Telegram alert: {e}")

    # ── Main Fetch ────────────────────────────────────────────────────────────
    @staticmethod
    async def fetch_all_realtime():
        sensors = []
        new_alerts = []
        total_cosmic_energy = 0.0

        async with httpx.AsyncClient() as client:
            try:
                resp_usgs, resp_nasa, resp_solar = await asyncio.gather(
                    client.get(DisasterService.USGS_URL, timeout=30.0),
                    client.get(DisasterService.NASA_EONET, timeout=30.0),
                    client.get(DisasterService.NASA_SOLAR, timeout=20.0),
                    return_exceptions=True,
                )

                # ── 1. USGS (Earthquakes) ────────────────────────────────────
                if isinstance(resp_usgs, httpx.Response) and resp_usgs.status_code == 200:
                    features = resp_usgs.json().get("features", [])
                    logger.info(f"[DISASTER SVC] USGS returned {len(features)} raw events.")

                    for q in features:
                        props = q["properties"]
                        mag = props.get("mag", 0) or 0
                        if mag < 1.0:
                            continue

                        place = props["place"]
                        energy = min(max(mag / 9.0, 0.0), 1.0)

                        if mag >= 6.0:
                            msg = (
                                f"🚨 [EARTHQUAKE] Động đất lớn!\n"
                                f"Vị trí: {place}\nCường độ: {mag} Richter"
                            )
                            if place not in DisasterService.alerted_events:
                                DisasterService.alerted_events.add(place)
                                new_alerts.append(msg)
                                logger.warning(
                                    f"[DISASTER SVC] Major earthquake M{mag} at {place} — "
                                    "triggering reactor shock."
                                )
                                upt_reactor.update_external_stress(energy)

                        sensors.append({
                            "type": "EARTHQUAKE",
                            "place": place,
                            "lat": q["geometry"]["coordinates"][1],
                            "lon": q["geometry"]["coordinates"][0],
                            "energy_level": energy,
                            "anomaly_score": props.get("sig", 0) / 1000.0,
                            "raw_val": mag,
                            "timestamp": props.get("time", 0),
                        })
                else:
                    logger.error(
                        f"[DISASTER SVC] USGS fetch failed: {resp_usgs}"
                    )

                # ── 2. NASA EONET (Surface Disasters) ────────────────────────
                if isinstance(resp_nasa, httpx.Response) and resp_nasa.status_code == 200:
                    events = resp_nasa.json().get("events", [])
                    logger.info(f"[DISASTER SVC] NASA EONET returned {len(events)} events.")

                    meta = {
                        "wildfires":    ("WILDFIRE", 0.75),
                        "volcanoes":    ("VOLCANO",  0.95),
                        "severeStorms": ("STORM",    0.85),
                        "seaLakeIce":   ("ICEBERG",  0.40),
                    }

                    for ev in events[:500]:
                        if not ev.get("geometry"):
                            continue
                        cat = ev["categories"][0]["id"]
                        geo_raw = ev["geometry"][0]["coordinates"]

                        # Handle Point vs Polygon coordinates
                        if isinstance(geo_raw[0], list):
                            lon, lat = geo_raw[0][0], geo_raw[0][1]
                        else:
                            lon, lat = geo_raw[0], geo_raw[1]

                        if cat in meta:
                            d_type, energy = meta[cat]
                            date_str = ev["geometry"][0].get("date", "")
                            ts = 0
                            if date_str:
                                try:
                                    ts = int(datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp() * 1000)
                                except Exception:
                                    ts = int(datetime.now(timezone.utc).timestamp() * 1000)
                            
                            sensors.append({
                                "type": d_type,
                                "place": ev["title"],
                                "lat": lat, "lon": lon,
                                "energy_level": energy,
                                "anomaly_score": 0.6,
                                "raw_val": 5.0,
                                "timestamp": ts,
                            })
                else:
                    logger.error(
                        f"[DISASTER SVC] NASA EONET fetch failed: {resp_nasa}"
                    )

                # ── 3. NASA DONKI (Solar Flares) ─────────────────────────────
                if isinstance(resp_solar, httpx.Response) and resp_solar.status_code == 200:
                    flares = resp_solar.json()
                    if flares and isinstance(flares, list):
                        latest_flares = sorted(
                            flares, key=lambda x: x.get("beginTime", ""), reverse=True
                        )[:3]
                        logger.info(
                            f"[DISASTER SVC] NASA DONKI: {len(latest_flares)} recent solar flares."
                        )

                        for flare in latest_flares:
                            class_type = flare.get("classType", "B")
                            energy = 0.1
                            if "C" in class_type: energy = 0.3
                            if "M" in class_type: energy = 0.6
                            if "X" in class_type: energy = 1.0

                            total_cosmic_energy = max(total_cosmic_energy, energy)
                            
                            date_str = flare.get("beginTime", "")
                            ts = 0
                            if date_str:
                                try:
                                    ts = int(datetime.fromisoformat(date_str.replace("Z", "+00:00")).timestamp() * 1000)
                                except Exception:
                                    ts = int(datetime.now(timezone.utc).timestamp() * 1000)

                            sensors.append({
                                "type": "SOLAR_FLARE",
                                "place": f"Sunspot {flare.get('activeRegionNum', 'Unknown')} ({class_type})",
                                "lat": 90.0, "lon": 0.0,
                                "energy_level": energy,
                                "anomaly_score": 0.99,
                                "raw_val": energy * 10,
                                "timestamp": ts,
                            })
                else:
                    logger.warning(
                        f"[DISASTER SVC] NASA DONKI fetch failed or returned no data: {resp_solar}"
                    )

            except Exception as e:
                logger.exception(f"[DISASTER SVC] Critical error during data fetch: {e}")

        # ── Cosmic Coupling → Reactor ─────────────────────────────────────────
        if total_cosmic_energy > 0:
            coupling_factor = UPTMath.calculate_geomagnetic_coupling(total_cosmic_energy)
            if coupling_factor > 0.1:
                upt_reactor.inject_cosmic_interference(coupling_factor)
                if coupling_factor > 0.4:
                    msg = (
                        f"⚠️ [COSMIC ALERT] Phát hiện Bão từ mạnh!\n"
                        f"Hệ số liên kết: {coupling_factor:.3f}\n"
                        "Lò phản ứng đang chịu nhiễu loạn pha."
                    )
                    if "COSMIC_STORM" not in DisasterService.alerted_events:
                        DisasterService.alerted_events.add("COSMIC_STORM")
                        new_alerts.append(msg)
                        logger.critical(
                            f"[DISASTER SVC] 🌌 COSMIC STORM — coupling={coupling_factor:.3f}"
                        )

        for msg in new_alerts:
            await DisasterService.send_telegram_alert(msg)

        if sensors:
            DisasterService.LATEST_DATA = sensors
            logger.info(f"[DISASTER SVC] ✅ Cache updated with {len(sensors)} global events.")

            # Feed real data into the AI brain
            guardian_brain.update_realtime_state(sensors)

            # Persist snapshot to MongoDB
            try:
                collection = Database.get_collection("raw_logs")
                if collection is not None:
                    log_entry = {
                        "timestamp": datetime.now(timezone.utc),
                        "total_events": len(sensors),
                        "max_magnitude": max(s["raw_val"] for s in sensors) if sensors else 0,
                        "sensors_data": sensors,
                    }
                    collection.insert_one(log_entry)
                    logger.debug("[DISASTER SVC] Snapshot saved to MongoDB.")
            except Exception as e:
                logger.error(f"[DISASTER SVC] MongoDB save failed: {e}")

        return sensors

    @staticmethod
    def get_latest_data():
        return DisasterService.LATEST_DATA