import os
import pymongo
import pandas as pd
from dotenv import load_dotenv

def export_data():
    print("Loading environment variables...")
    # Load .env from parent directory properly
    dotenv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    load_dotenv(dotenv_path=dotenv_path)
    
    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        print("Error: MONGO_URI not found.")
        return
        
    print(f"Connecting to MongoDB...")
    client = pymongo.MongoClient(mongo_uri)
    db = client["upt_guardian"]
    
    print("Fetching data from raw_logs collection...")
    logs = list(db.raw_logs.find({}))
    
    if not logs:
        print("No data found in raw_logs. Has the system fetched data yet?")
        return
        
    print(f"Found {len(logs)} log cycles. Parsing sensor data...")
    records = []
    for log in logs:
        log_time = log.get("timestamp")
        sensors = log.get("sensors_data", [])
        for s in sensors:
            records.append({
                "log_timestamp": log_time,
                "sensor_id": s.get("id"),
                "event_type": s.get("type"),
                "lat": s.get("lat"),
                "lng": s.get("lon", s.get("lng")),
                "magnitude": s.get("mag"),
                "raw_val": s.get("raw_val")
            })
            
    df = pd.DataFrame(records)
    
    if df.empty:
        print("No valid sensors_data found inside the logs.")
        return
        
    # Optional: Convert log_timestamp to datetime object
    df['log_timestamp'] = pd.to_datetime(df['log_timestamp'])
    
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sensors.csv")
    df.to_csv(output_path, index=False)
    print(f"\n[SUCCESS] Exported {len(df)} individual sensor events to {output_path}")
    print(df.head())

if __name__ == "__main__":
    export_data()
