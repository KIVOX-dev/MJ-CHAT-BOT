import os
import requests
import json
import time
import socket

def check_port(host, port):
    """Checks if a port is open."""
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False

def check_ollama():
    print("[*] Checking Ollama (Port 11434)...")
    
    if not check_port("127.0.0.1", 11434):
        print(" [!] Port 11434 is CLOSED. Ollama is likely not running.")
        return False
        
    print(" [+] Port 11434 is OPEN. Testing API response...")
    try:
        res = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if res.status_code == 200:
            models = [m['name'] for m in res.json().get('models', [])]
            print(f" [+] Ollama is ONLINE. Models: {', '.join(models)}")
            return True
        else:
            print(f" [!] Ollama API returned error: {res.status_code}")
    except Exception as e:
        print(f" [!] Ollama API is not responding correctly: {e}")
    return False

def check_mongo():
    print("[*] Checking MongoDB...")
    from memory import MemoryLayer
    mem = MemoryLayer()
    if mem.client:
        try:
            mem.client.server_info()
            print(" [+] MongoDB is ONLINE and REACHABLE.")
            return True
        except Exception as e:
            print(f" [!] MongoDB login failed: {e}")
    else:
        print(" [!] MongoDB URI not found in .env")
    return False

def check_cloud():
    print("[*] Checking Cloud AI (Gemini)...")
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        print(f" [+] Gemini API Key detected. (Starts with: {GEMINI_API_KEY[:5]}...)")
        return True
    else:
        print(" [!] Gemini API Key MISSING from .env")
    return False

def run_diagnostics():
    print("-" * 40)
    print(" MJ AI SYSTEM DIAGNOSTIC REPORT")
    print("-" * 40)
    
    o = check_ollama()
    m = check_mongo()
    c = check_cloud()
    
    print("-" * 40)
    if o and m and c:
        print(" [SUCCESS] All systems are GO. MJ AI is fully functional.")
    else:
        print(" [WARNING] Some systems are degraded. See errors above.")
    print("-" * 40)

if __name__ == "__main__":
    run_diagnostics()
