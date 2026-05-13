from twilio.rest import Client
from app.core.config import settings
from app.core.logger import get_logger
from app.core.database import Database
from datetime import datetime, timezone

logger = get_logger(__name__)

class AlertService:
    @staticmethod
    def _get_client():
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            return None
        try:
            return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        except Exception as e:
            logger.error(f"[ALERT SERVICE] Failed to initialize Twilio client: {e}")
            return None

    @staticmethod
    def subscribe(phone_number: str, region: str = "GLOBAL"):
        """Save a new subscriber to MongoDB."""
        col = Database.get_collection("alerts_subscribers")
        if col is None:
            logger.error("[ALERT SERVICE] Cannot subscribe: Database not connected.")
            return False
            
        try:
            # Upsert to prevent duplicates
            col.update_one(
                {"phone_number": phone_number},
                {"$set": {
                    "phone_number": phone_number,
                    "region": region,
                    "subscribed_at": datetime.now(timezone.utc)
                }},
                upsert=True
            )
            logger.info(f"[ALERT SERVICE] Subscribed new number: {phone_number} for region {region}")
            return True
        except Exception as e:
            logger.error(f"[ALERT SERVICE] Subscription failed: {e}")
            return False

    @staticmethod
    def send_critical_alert(lat: float, lon: float, risk: float, alert_level: str):
        """Send SMS to all subscribers."""
        client = AlertService._get_client()
        if not client:
            logger.warning("[ALERT SERVICE] SMS sending skipped: Twilio not configured.")
            return
            
        col = Database.get_collection("alerts_subscribers")
        if col is None:
            return
            
        subscribers = list(col.find({}))
        if not subscribers:
            return
            
        msg_body = (
            f"🚨 UPT GUARDIAN ALERT 🚨\n"
            f"RISK LEVEL: {alert_level} ({risk*100:.1f}%)\n"
            f"LOCATION: Lat {lat:.2f}, Lon {lon:.2f}\n"
            f"Immediate action recommended!"
        )
        
        logger.info(f"[ALERT SERVICE] Broadcasting SMS to {len(subscribers)} subscribers...")
        
        success_count = 0
        for sub in subscribers:
            phone = sub.get("phone_number")
            if not phone:
                continue
                
            # Chuẩn hóa số điện thoại: Xóa khoảng trắng
            phone = phone.replace(" ", "")
                
            try:
                client.messages.create(
                    body=msg_body,
                    from_=settings.TWILIO_FROM_NUMBER,
                    to=phone
                )
                success_count += 1
            except Exception as e:
                logger.error(f"[ALERT SERVICE] Failed to send SMS to {phone}: {e}")
                
        logger.info(f"[ALERT SERVICE] Broadcast complete. Sent {success_count}/{len(subscribers)} SMS.")
