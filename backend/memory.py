import json
import os
import pymongo
import time
import re
from config import MONGO_URI, MEMORY_FILE
from typing import List, Dict, Any, Optional

# Ownership model: every record has an "owner" identity string (the value
# FastAPI's auth dependency resolves the caller's bearer token to - see
# auth.py). Records written before this existed, and anything imported by
# offline scripts (ingest.py, train_mcq.py) that never pass owner=, default
# to "default". "default" therefore doubles as the shared/legacy knowledge
# bucket: every identity can see it, but identities only ever see their own
# private conversational records otherwise. This is what actually closes
# the IDOR in server.py's /api/sessions and /api/history/{id} - those now
# require an owner and can only return that owner's own data.
_SHARED_OWNER = "default"


def _owner_of(record: Dict[str, Any]) -> str:
    return record.get("owner", _SHARED_OWNER)


def _is_private_match(record: Dict[str, Any], owner: str) -> bool:
    """True if `record` belongs to `owner` (or is legacy data and owner is default)."""
    return _owner_of(record) == owner


def _is_visible_match(record: Dict[str, Any], owner: str) -> bool:
    """True if `record` should be visible to `owner`: their own data, or shared/legacy data."""
    record_owner = _owner_of(record)
    return record_owner == owner or record_owner == _SHARED_OWNER


def _mongo_private_filter(owner: str) -> Dict[str, Any]:
    if owner == _SHARED_OWNER:
        return {"$or": [{"owner": _SHARED_OWNER}, {"owner": {"$exists": False}}]}
    return {"owner": owner}


def _mongo_visible_filter(owner: str) -> Dict[str, Any]:
    if owner == _SHARED_OWNER:
        return _mongo_private_filter(_SHARED_OWNER)
    return {"$or": [{"owner": owner}, {"owner": _SHARED_OWNER}, {"owner": {"$exists": False}}]}


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

    def read_all(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns every record when `owner` is None (used internally by the
        learning/training pipeline, which is a shared local classifier, not
        per-identity), or only records visible to `owner` otherwise (used by
        the /api/metrics route).
        """
        if self.local_mode:
            data = self._read_local()
            if owner is None:
                return data
            return [m for m in data if _is_visible_match(m, owner)]

        if not self.collection: return []
        try:
            mongo_filter = {} if owner is None else _mongo_visible_filter(owner)
            return list(self.collection.find(mongo_filter, {"_id": 0}))
        except Exception as e:
            print(f"Error reading memory: {e}")
            return []

    def get_session_history(self, session_id: str, owner: str) -> List[Dict[str, Any]]:
        """Retrieves messages for a specific session sorted by time, scoped to `owner`."""
        if self.local_mode:
            local_data = self._read_local()
            filtered = [
                m for m in local_data
                if m.get("session_id") == session_id and _is_private_match(m, owner)
            ]
            filtered.sort(key=lambda x: x.get("timestamp", 0))
            return filtered

        if not self.collection: return []
        try:
            query = {"session_id": session_id, **_mongo_private_filter(owner)}
            return list(self.collection.find(query, {"_id": 0}).sort("_id", 1))
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []

    def list_sessions(self, owner: str) -> List[str]:
        """Returns unique session IDs belonging to `owner` for the sidebar."""
        if self.local_mode:
            local_data = self._read_local()
            sessions = set()
            for m in local_data:
                sid = m.get("session_id")
                if sid and _is_private_match(m, owner):
                    sessions.add(sid)
            return list(sessions)

        if not self.collection: return []
        try:
            return self.collection.distinct("session_id", _mongo_private_filter(owner))
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []

    def store(self, input_text: str, output_text: str, context: str, source: str, confidence: str, tags: List[str], latency_ms: float = 0.0, session_id: str = "default", owner: str = _SHARED_OWNER):
        new_entry = {
            "input": input_text,
            "output": output_text,
            "context": context,
            "source": source,
            "confidence": confidence,
            "tags": tags,
            "latency_ms": latency_ms,
            "session_id": session_id,
            "owner": owner,
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

    def set_feedback(self, memory_id: str, feedback_type: str, owner: str):
        """Updates a memory record with user feedback (up/down), scoped to `owner`."""
        if self.local_mode:
            local_data = self._read_local()
            updated = False
            for record in local_data:
                if record.get("id") == memory_id and _is_private_match(record, owner):
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
            owner_filter = _mongo_private_filter(owner)
            record = self.collection.find_one({"_id": ObjectId(memory_id), **owner_filter})
            if not record:
                return False

            update_data = {"$set": {"feedback": feedback_type}}

            # If feedback is 'up', also promote 'pending-confirmation' to 'verified-persistent'
            if feedback_type == "up" and "pending-confirmation" in record.get("tags", []):
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

    def confirm_memory(self, session_id: str, owner: str):
        """Promotes the most recent 'pending-confirmation' memory in a session with extraction."""
        if self.local_mode:
            local_data = self._read_local()
            for record in reversed(local_data):
                if (
                    record.get("session_id") == session_id
                    and _is_private_match(record, owner)
                    and "pending-confirmation" in record.get("tags", [])
                ):
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
            query = {"session_id": session_id, "tags": "pending-confirmation", **_mongo_private_filter(owner)}
            latest_pending = self.collection.find_one(query, sort=[("_id", -1)])
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

    def reject_memory(self, session_id: str, owner: str):
        """Discards the most recent 'pending-confirmation' memory in a session."""
        if self.local_mode:
            local_data = self._read_local()
            for idx, record in enumerate(reversed(local_data)):
                if (
                    record.get("session_id") == session_id
                    and _is_private_match(record, owner)
                    and "pending-confirmation" in record.get("tags", [])
                ):
                    # Remove from original list
                    local_data.pop(len(local_data) - 1 - idx)
                    self._write_local(local_data)
                    return True
            return False

        if not self.collection: return False
        try:
            query = {"session_id": session_id, "tags": "pending-confirmation", **_mongo_private_filter(owner)}
            latest_pending = self.collection.find_one(query, sort=[("_id", -1)])
            if latest_pending:
                self.collection.delete_one({"_id": latest_pending["_id"]})
                return True
        except Exception as e:
            print(f"Error rejecting memory: {e}")
        return False

    def find_relevant(self, query: str, owner: str = _SHARED_OWNER) -> List[Dict[str, Any]]:
        """
        Context lookup for prompt augmentation. Visible to `owner`: their own
        past turns plus shared/legacy knowledge (imported datasets, and
        anything stored under the default identity) - never another
        identity's private conversation history.
        """
        if self.local_mode:
            local_data = self._read_local()
            results = []
            verified_results = []

            # re.escape: `query` is free-text user input, not a pattern the
            # caller intends as a regex. Without escaping it, characters
            # like `(`, `*`, `+` either raise on compile or - worse - let a
            # crafted query cause catastrophic backtracking (ReDoS) against
            # every stored input (CWE-1333).
            rx = re.compile(re.escape(query), re.IGNORECASE)

            for m in local_data:
                if not _is_visible_match(m, owner):
                    continue
                input_val = m.get("input", "")
                if rx.search(input_val):
                    if "verified-persistent" in m.get("tags", []):
                        verified_results.append(m)
                    else:
                        results.append(m)

            # Limit like MongoDB does
            return verified_results[:3] + results[:3]

        if not self.collection: return []
        try:
            visible_filter = _mongo_visible_filter(owner)
            safe_pattern = re.escape(query)  # see local_mode branch above (CWE-1333 / injection)

            # 1. Search regular logs (conversational)
            regex_query = {"input": {"$regex": safe_pattern, "$options": "i"}, **visible_filter}
            results = list(self.collection.find(regex_query, {"_id": 0}).limit(3))

            # 2. Search prioritized knowledge (verified-persistent)
            verified_query = {"tags": "verified-persistent", "input": {"$regex": safe_pattern, "$options": "i"}, **visible_filter}
            verified_results = list(self.collection.find(verified_query, {"_id": 0}).limit(3))

            # Combined, prioritized
            return verified_results + results
        except Exception as e:
            print(f"Error searching memory: {e}")
            return []
