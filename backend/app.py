# pyrefly: ignore [missing-import]
from flask import Flask, request, jsonify, send_from_directory
from main import autonomous_loop
import os
import sys


# Add backend directory to the path so relative imports work correctly
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from backend.app import app

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(app.static_folder, path)

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    query = data.get('query', '')
    if not query:
        return jsonify({"error": "No query provided"})
        
    result = autonomous_loop(query)
    return jsonify(result)

@app.route('/api/metrics', methods=['GET'])
def metrics():
    import json
    mem_path = 'memory.json'
    if not os.path.exists(mem_path):
        return jsonify({"total": 0, "sources": {}, "tags": {}})
    
    try:
        with open(mem_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        data = []
        
    sources = {"PyTorch Natively": 0, "SymPy Math Engine": 0, "Gemini Fallback": 0, "Global Web Hooks": 0}
    tags = {}
    factbook_count = 0
    
    for item in data:
        item_tags = item.get("tags", [])
        if "cia-factbook" in item_tags:
            factbook_count += 1
            
        src = item.get("source", "")
        if "Internal PyTorch Model" in src:
            sources["PyTorch Natively"] += 1
        elif "Math Engine" in src:
            sources["SymPy Math Engine"] += 1
        elif "Wikipedia:" in src or "DuckDuckGo" in src:
            sources["Global Web Hooks"] += 1
        else:
            sources["Gemini Fallback"] += 1
            
        for tag in item.get("tags", []):
            tags[tag] = tags.get(tag, 0) + 1
            
    latencies = [item.get("latency_ms", 0) for item in data if "latency_ms" in item]
    latencies = latencies[-20:] # keep last 20 for graph
            
    return jsonify({
        "total": len(data),
        "sources": sources,
        "tags": tags,
        "latencies": latencies,
        "high_fidelity_count": factbook_count
    })

if __name__ == '__main__':
    # RedSage Patch: Disable debug=True for security (CWE-94)
    app.run(host='0.0.0.0', port=5001, debug=False)
