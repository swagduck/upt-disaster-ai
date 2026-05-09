"""
MongoDB connection manager with lazy initialization.

Connection is established on first use (via ``ensure_connected()``),
not at import time — making the module test-friendly and avoiding
blocking the import chain when the DB is unreachable.
"""
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class Database:
    client: MongoClient | None = None
    db = None
    _connected: bool = False

    @staticmethod
    def connect():
        """Attempt to connect to MongoDB Atlas. Safe to call multiple times."""
        if Database._connected:
            return

        uri = settings.MONGO_URI
        db_name = settings.DB_NAME

        if not uri:
            logger.warning("[DATABASE] No MONGO_URI configured — running without persistence.")
            Database._connected = True  # Mark as "attempted" so we don't retry
            return

        try:
            # Thiết lập timeout 3 giây để tránh treo ứng dụng khi không kết nối được MongoDB trên Render
            Database.client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            # Verify connectivity
            Database.client.admin.command("ping")
            Database.db = Database.client[db_name]
            logger.info(f"[DATABASE] Connected to MongoDB Atlas: {db_name}")

            # Initialize raw_logs as Time-Series collection if it doesn't exist
            if "raw_logs" not in Database.db.list_collection_names():
                try:
                    Database.db.create_collection(
                        "raw_logs",
                        timeseries={
                            "timeField": "timestamp",
                            "granularity": "minutes"
                        }
                    )
                    logger.info("[DATABASE] Initialized 'raw_logs' as Time-Series Collection.")
                except Exception as e:
                    logger.warning(f"[DATABASE] Could not create Time-Series collection (might not be supported): {e}")

            # Ensure index exists (useful if it's a regular collection)
            Database.db.raw_logs.create_index("timestamp")

        except ConnectionFailure as e:
            logger.error(f"[DATABASE] Connection failed: {e}")
        except Exception as e:
            logger.exception(f"[DATABASE] Unexpected error during connect: {e}")
        finally:
            Database._connected = True

    @staticmethod
    def ensure_connected():
        """Lazy connection — call this before first DB use."""
        if not Database._connected:
            Database.connect()

    @staticmethod
    def get_collection(name):
        Database.ensure_connected()
        if Database.db is not None:
            return Database.db[name]
        return None