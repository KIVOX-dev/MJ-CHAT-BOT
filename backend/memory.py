import json
import os
import pymongo
import time
import re
from config import MONGO_URI, MEMORY_FILE
from typing import List, Dict, Any

class MemoryLayer:
    def __init__(self, uri: str = MONGO_URI):
        self.local_mode = False
        if not uri:
            print("[!] Warning: MONGO_URI not found. Falling back to local memory.json operations.")
            self.client = None
            self.collection = None
            self.local_mode = True
            return

        try:
            self.client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.client["rem_ai"]
            self.collection = self.db["memories"]
            # Test connection
            self.client.server_info()
        except Exception as e:
            print(f"[!] MongoDB Connection Error: {e}. Falling back to local memory.json operations.")
            self.client = None
            self.collection = None
            self.local_mode = True

    def _read_local(self) -> List[Dict[str, Any]]:
        if not os.path.exists(MEMORY_FILE):
            return []
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading local memory file: {e}")
            return []

    def _write_local(self, data: List[Dict[str, Any]]):
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error writing local memory file: {e}")

    def read_all(self) -> List[Dict[str, Any]]:
        if self.local_mode:
            return self._read_local()
        
        if not self.collection: return []
        try:
            return list(self.collection.find({}, {"_id": 0}))
        except Exception as e:
            print(f"Error reading memory: {e}")
            return []

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Retrieves messages for a specific session sorted by time."""
        if self.local_mode:
            local_data = self._read_local()
            # Sort by timestamp (or insertion order)
            filtered = [m for m in local_data if m.get("session_id") == session_id]
            filtered.sort(key=lambda x: x.get("timestamp", 0))
            return filtered

        if not self.collection: return []
        try:
            return list(self.collection.find({"session_id": session_id}, {"_id": 0}).sort("_id", 1))
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []

    def list_sessions(self) -> List[str]:
        """Returns unique session IDs for the sidebar."""
        if self.local_mode:
            local_data = self._read_local()
            sessions = set()
            for m in local_data:
                sid = m.get("session_id")
                if sid:
                    sessions.add(sid)
            return list(sessions)

        if not self.collection: return []
        try:
            return self.collection.distinct("session_id")
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []
            
    def store(self, input_text: str, output_text: str, context: str, source: str, confidence: str, tags: List[str], latency_ms: float = 0.0, session_id: str = "default"):
        new_entry = {
            "input": input_text,
            "output": output_text,
            "context": context,
            "source": source,
            "confidence": confidence,
            "tags": tags,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "timestamp": time.time(),
            "feedback": None
        }

        if self.local_mode:
            local_data = self._read_local()
            # Simulate a unique string ID using timestamp + index
            entry_id = f"local_{int(time.time())}_{len(local_data)}"
            new_entry["id"] = entry_id
            local_data.append(new_entry)
            self._write_local(local_data)
            return entry_id

        if not self.collection: return None
        try:
            result = self.collection.insert_one(new_entry)
            return str(result.inserted_id)
        except Exception as e:
            print(f"Error storing memory: {e}")
            return None

    def set_feedback(self, memory_id: str, feedback_type: str):
        """Updates a memory record with user feedback (up/down)."""
        if self.local_mode:
            local_data = self._read_local()
            updated = False
            for record in local_data:
                if record.get("id") == memory_id:
                    record["feedback"] = feedback_type
                    # If feedback is 'up', promote tag
                    if feedback_type == "up" and "pending-confirmation" in record.get("tags", []):
                        output = record.get("output", "")
                        match = re.search(r"\[MEM_SUMMARY:\s*(.*?)\]", output, re.DOTALL)
                        clean_output = match.group(1).strip() if match else output
                        record["tags"] = ["verified-persistent"]
                        record["output"] = clean_output
                    updated = True
                    break
            if updated:
                self._write_local(local_data)
                return True
            return False

        if not self.collection: return False
        try:
            from bson.objectid import ObjectId
            update_data = {"$set": {"feedback": feedback_type}}
            
            # If feedback is 'up', also promote 'pending-confirmation' to 'verified-persistent'
            if feedback_type == "up":
                record = self.collection.find_one({"_id": ObjectId(memory_id), "tags": "pending-confirmation"})
                if record:
                    output = record.get("output", "")
                    # Extract clean summary
                    match = re.search(r"\[MEM_SUMMARY:\s*(.*?)\]", output, re.DOTALL)
                    clean_output = match.group(1).strip() if match else output
                    
                    self.collection.update_one(
                        {"_id": ObjectId(memory_id)},
                        {"$set": {"tags": ["verified-persistent"], "output": clean_output}}
                    )
                
            self.collection.update_one(
                {"_id": ObjectId(memory_id)},
                update_data
            )
            return True
        except Exception as e:
            print(f"Error setting feedback: {e}")
            return False

    def confirm_memory(self, session_id: str):
        """Promotes the most recent 'pending-confirmation' memory in a session with extraction."""
        if self.local_mode:
            local_data = self._read_local()
            for record in reversed(local_data):
                if record.get("session_id") == session_id and "pending-confirmation" in record.get("tags", []):
                    output = record.get("output", "")
                    match = re.search(r"\[MEM_SUMMARY:\s*(.*?)\]", output, re.DOTALL)
                    clean_output = match.group(1).strip() if match else output
                    record["tags"] = ["verified-persistent"]
                    record["output"] = clean_output
                    self._write_local(local_data)
                    return True
            return False

        if not self.collection: return False
        try:
            latest_pending = self.collection.find_one(
                {"session_id": session_id, "tags": "pending-confirmation"},
                sort=[("_id", -1)]
            )
            if latest_pending:
                output = latest_pending.get("output", "")
                # Extract clean summary
                match = re.search(r"\[MEM_SUMMARY:\s*(.*?)\]", output, re.DOTALL)
                clean_output = match.group(1).strip() if match else output
                
                self.collection.update_one(
                    {"_id": latest_pending["_id"]},
                    {"$set": {"tags": ["verified-persistent"], "output": clean_output}}
                )
                return True
        except Exception as e:
            print(f"Error confirming memory: {e}")
        return False

    def reject_memory(self, session_id: str):
        """Discards the most recent 'pending-confirmation' memory in a session."""
        if self.local_mode:
            local_data = self._read_local()
            for idx, record in enumerate(reversed(local_data)):
                if record.get("session_id") == session_id and "pending-confirmation" in record.get("tags", []):
                    # Remove from original list
                    local_data.pop(len(local_data) - 1 - idx)
                    self._write_local(local_data)
                    return True
            return False

        if not self.collection: return False
        try:
            latest_pending = self.collection.find_one(
                {"session_id": session_id, "tags": "pending-confirmation"},
                sort=[("_id", -1)]
            )
            if latest_pending:
                self.collection.delete_one({"_id": latest_pending["_id"]})
                return True
        except Exception as e:
            print(f"Error rejecting memory: {e}")
        return False

    def find_relevant(self, query: str) -> List[Dict[str, Any]]:
        if self.local_mode:
            local_data = self._read_local()
            # Regex search emulation locally
            results = []
            verified_results = []
            
            try:
                rx = re.compile(query, re.IGNORECASE)
            except Exception:
                rx = None
            
            for m in local_data:
                input_val = m.get("input", "")
                match = False
                if rx:
                    match = rx.search(input_val) is not None
                else:
                    match = query.lower() in input_val.lower()
                
                if match:
                    if "verified-persistent" in m.get("tags", []):
                        verified_results.append(m)
                    else:
                        results.append(m)
            
            # Limit like MongoDB does
            return verified_results[:3] + results[:3]

        if not self.collection: return []
        try:
            # 1. Search regular logs (conversational)
            regex_query = {"input": {"$regex": query, "$options": "i"}}
            results = list(self.collection.find(regex_query, {"_id": 0}).limit(3))
            
            # 2. Search prioritized knowledge (verified-persistent)
            verified_query = {"tags": "verified-persistent", "input": {"$regex": query, "$options": "i"}}
            verified_results = list(self.collection.find(verified_query, {"_id": 0}).limit(3))
            
            # Combined, prioritized
            return verified_results + results
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []
