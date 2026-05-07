from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class Database:
    client: MongoClient = None
    db = None

    @staticmethod
    def connect():
        uri = settings.MONGO_URI
        db_name = settings.DB_NAME

        if not uri:
            logger.warning("[DATABASE] No MONGO_URI configured — running without persistence.")
            return

        try:
            Database.client = MongoClient(uri)
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

    @staticmethod
    def get_collection(name):
        if Database.db is not None:
            return Database.db[name]
        return None


# Establish connection at import time
Database.connect()