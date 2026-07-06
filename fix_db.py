import pymongo
import os
from dotenv import load_dotenv

load_dotenv()
db = pymongo.MongoClient(os.getenv('MONGO_URI'))['upt_guardian']

docs = db.raw_logs.find({'max_magnitude': {'$gte': 10.0}})
count = 0
for d in docs:
    sensors = d.get('sensors_data', [])
    earthquake_vals = [s.get('raw_val', 0) for s in sensors if s.get('type') == 'EARTHQUAKE']
    real_max = max(earthquake_vals) if earthquake_vals else 0
    db.raw_logs.update_one({'_id': d['_id']}, {'$set': {'max_magnitude': real_max}})
    count += 1

print(f"Updated {count} documents")
