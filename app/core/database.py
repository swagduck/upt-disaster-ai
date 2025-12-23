from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

class Database:
    client: MongoClient = None
    db = None

    @staticmethod
    def connect():
        uri = os.getenv("MONGO_URI")
        db_name = os.getenv("DB_NAME", "upt_guardian")
        
        if not uri:
            print("⚠️ [DATABASE] No MONGO_URI found in .env")
            return

        try:
            Database.client = MongoClient(uri)
            # Kiểm tra kết nối
            Database.client.admin.command('ping')
            Database.db = Database.client[db_name]
            print(f"💾 [DATABASE] Connected to MongoDB Atlas: {db_name}")
            
            # Tạo index để tìm kiếm nhanh theo thời gian
            Database.db.raw_logs.create_index("timestamp")
            
        except ConnectionFailure as e:
            print(f"❌ [DATABASE] Connection Failed: {e}")

    @staticmethod
    def get_collection(name):
        if Database.db is not None:
            return Database.db[name]
        return None

# Khởi tạo kết nối ngay khi import
Database.connect()