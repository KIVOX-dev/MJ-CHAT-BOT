import pymongo
from config import MONGO_URI
import time

def test_connection():
    print(f"[*] Testing connection to: {MONGO_URI.split('@')[-1]}") # Hide credentials
    
    try:
        # Initializing client with short timeout
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        
        # Test 1: Network Latency / Server Info
        start = time.time()
        info = client.server_info()
        latency = round((time.time() - start) * 1000, 2)
        print(f"[+] Connected to MongoDB Atlas!")
        print(f"    - Server Version: {info.get('version')}")
        print(f"    - Connection Latency: {latency}ms")

        # Test 2: Database and Collection access
        db = client["rem_ai"]
        collection = db["memories"]
        count = collection.count_documents({})
        print(f"[+] 'rem_ai' database found.")
        print(f"[+] Total documents in 'memories': {count}")
        
        if count > 0:
            sample = collection.find_one({}, {"_id": 0, "input": 1})
            print(f"    - Sample Memory Found: '{sample.get('input')}'")
        
        print("\n[SUCCESS] MongoDB Connection is fully operational.")

    except Exception as e:
        print(f"\n[ERROR] Connection Failed: {e}")

if __name__ == "__main__":
    test_connection()
