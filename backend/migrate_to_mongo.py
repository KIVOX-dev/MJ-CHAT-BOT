import json
import os
import pymongo
from config import MONGO_URI, MEMORY_FILE

def migrate():
    print(f"[*] Starting migration from {MEMORY_FILE} to MongoDB Atlas...")
    
    if not os.path.exists(MEMORY_FILE):
        print("[!] No local memory file found. Nothing to migrate.")
        return

    with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
        local_data = json.load(f)

    if not local_data:
        print("[!] Local memory is empty.")
        return

    print(f"[*] Found {len(local_data)} entries locally. Connecting to MongoDB...")
    
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["rem_ai"]
        collection = db["memories"]
        
        # Migration logic
        inserted_count = 0
        for entry in local_data:
            # Check if exists in DB already (to avoid duplicates if script is re-run)
            if not collection.find_one({"input": entry["input"], "output": entry["output"]}):
                collection.insert_one(entry)
                inserted_count += 1
        
        print(f"[+] Migration complete! Successfully migrated {inserted_count} new entries.")
        print(f"[*] Total entries in Atlas now: {collection.count_documents({})}")
        
        # Optional: Rename local file as backup
        # os.rename(MEMORY_FILE, MEMORY_FILE + ".bak")
        # print(f"[*] Local backup created: {MEMORY_FILE}.bak")
        
    except Exception as e:
        print(f"[!] Migration Failed: {e}")

if __name__ == "__main__":
    migrate()
