import hmac

from fastapi import Depends, FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from main import autonomous_loop
from auth import get_current_identity
import os
import posixpath
import uvicorn
import asyncio
from typing import Optional
from config import TRAIN_INTERVAL, API_TOKENS, CHAT_RATE_LIMIT_AUTHENTICATED, CHAT_RATE_LIMIT_ANONYMOUS


def _resolve_identity_from_request(request: Request) -> Optional[str]:
    """Best-effort bearer-token -> identity lookup for rate-limit keying.

    Not a substitute for the get_current_identity auth dependency (this
    never rejects a request) - just lets the limiter charge authenticated
    callers against their own identity bucket instead of a shared IP bucket.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:].strip()
    for known_token, identity in API_TOKENS.items():
        if hmac.compare_digest(known_token, token):
            return identity
    return None


def _rate_limit_key(request: Request) -> str:
    identity = _resolve_identity_from_request(request)
    return f"identity:{identity}" if identity else f"ip:{get_remote_address(request)}"


def _chat_rate_limit(key: str) -> str:
    """Dynamic per-route limit for /api/chat: generous for a known identity,
    tighter for anything resolving to a bare IP (unauthenticated/bad token)."""
    return CHAT_RATE_LIMIT_AUTHENTICATED if key.startswith("identity:") else CHAT_RATE_LIMIT_ANONYMOUS


# Baseline limit applied (via SlowAPIMiddleware) to every route that doesn't
# declare its own @limiter.limit(...) - i.e. everything except /api/chat.
limiter = Limiter(key_func=_rate_limit_key, default_limits=[CHAT_RATE_LIMIT_ANONYMOUS])

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[*] Server starting...")
    try:
        # Import inside to avoid top-level issues
        from main import _learning_sys, _memory_sys
        def safe_train():
            try:
                _learning_sys.adapt_memory(_memory_sys)
            except Exception as e:
                print(f"[!] Background Training Failed: {e}")
        
        asyncio.create_task(asyncio.to_thread(safe_train))
        print("[+] Initial training task scheduled in background.")
    except Exception as e:
        print(f"[!] Startup training error: {e}")
    yield
    print("[*] Server shutting down.")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
# Resolved once at startup (follows symlinks) so every containment check below
# compares against the real on-disk root, not a symlinked alias of it.
FRONTEND_DIR_REAL = os.path.realpath(FRONTEND_DIR)


def _safe_static_path(requested_path: str):
    """
    Resolves `requested_path` against FRONTEND_DIR_REAL and returns the
    absolute filesystem path only if it stays inside that directory.

    Returns None for anything that would escape the static root: `..`
    traversal, absolute paths/drive letters, or symlinks that resolve
    outside the root (CWE-22).
    """
    if "\x00" in requested_path:
        return None

    # Anchor the path at a virtual root before normalizing: posixpath.normpath
    # collapses ".." segments against that anchor instead of letting them
    # climb past it, and os.path.isabs / drive-letter components in
    # `requested_path` are neutralized because we never join them directly.
    normalized = posixpath.normpath("/" + requested_path.replace("\\", "/")).lstrip("/")

    candidate = os.path.realpath(os.path.join(FRONTEND_DIR_REAL, normalized))

    try:
        if os.path.commonpath([candidate, FRONTEND_DIR_REAL]) != FRONTEND_DIR_REAL:
            return None
    except ValueError:
        # Raised on Windows when the two paths are on different drives -
        # that's an escape by definition.
        return None

    if not os.path.isfile(candidate):
        return None

    return candidate

app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Track how many new messages since last train
_new_messages_count = 0

# Mount UI static files
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.post("/api/chat")
@limiter.limit(_chat_rate_limit)
async def chat(request: Request, background_tasks: BackgroundTasks, identity: str = Depends(get_current_identity)):
    global _new_messages_count
    data = await request.json()
    query = data.get('query', '')
    session_id = data.get('session_id', 'default')

    if not query:
        return JSONResponse({"error": "No query provided"}, status_code=400)

    print(f"[FETCH] Received query for session {session_id} (identity={identity}): {query}")

    try:
        # Prevent the sync loop from blocking the FastAPI event loop
        result = await asyncio.to_thread(autonomous_loop, query, session_id, identity)
        
        # Increment counter and trigger background train if needed
        _new_messages_count += 1
        if _new_messages_count >= TRAIN_INTERVAL:
            print(f"[*] {TRAIN_INTERVAL} new memories reached. Triggering background re-train...")
            from main import _learning_sys, _memory_sys
            background_tasks.add_task(_learning_sys.adapt_memory, _memory_sys)
            _new_messages_count = 0
            
        print(f"[REPLY] Returning result from: {result['source']}")
        return JSONResponse(result)
    except Exception as e:
        print(f"[!] Server Error in /api/chat: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/api/sessions")
async def list_sessions(identity: str = Depends(get_current_identity)):
    from memory import MemoryLayer
    mem = MemoryLayer()
    sessions = mem.list_sessions(identity)
    return JSONResponse({"sessions": sessions})

@app.get("/api/history/{session_id}")
async def get_history(session_id: str, identity: str = Depends(get_current_identity)):
    from memory import MemoryLayer
    mem = MemoryLayer()
    history = mem.get_session_history(session_id, identity)
    return JSONResponse({"history": history})

@app.post("/api/feedback")
async def feedback(request: Request, identity: str = Depends(get_current_identity)):
    data = await request.json()
    msg_id = data.get('message_id')
    f_type = data.get('type')

    if not msg_id or not f_type:
        return JSONResponse({"error": "Missing ID or type"}, status_code=400)

    print(f"[FEEDBACK] {msg_id} -> {f_type} (identity={identity})")
    from memory import MemoryLayer
    mem = MemoryLayer()
    success = mem.set_feedback(msg_id, f_type, identity)

    return JSONResponse({"status": "ok" if success else "error"})

@app.get("/api/metrics")
async def metrics(identity: str = Depends(get_current_identity)):
    from memory import MemoryLayer
    memory_sys = MemoryLayer()
    data = memory_sys.read_all(identity)
    
    # Initialize categories
    sources = {
        "BERT Ensemble": 0,
        "Researcher Engine": 0, 
        "Ollama (Local)": 0,
        "Cloud Fallback": 0
    }
    tags = {}
    
    for item in data:
        item_tags = item.get("tags", [])
        
        src = item.get("source", "")
        if "Ensemble" in src:
            sources["BERT Ensemble"] += 1
        elif any(x in src for x in ["Wikipedia", "DuckDuckGo", "Researcher"]) or item.get("web_used"):
            sources["Researcher Engine"] += 1
        elif "Ollama" in src:
            sources["Ollama (Local)"] += 1
        else:
            sources["Cloud Fallback"] += 1
            
        for tag in item_tags:
            tags[tag] = tags.get(tag, 0) + 1
            
    latencies = [item.get("latency_ms", 0) for item in data if "latency_ms" in item]
    latencies = latencies[-20:]
            
    return JSONResponse({
        "total": len(data),
        "sources": sources,
        "tags": tags,
        "latencies": latencies,
        "verified_memory_count": tags.get("verified-persistent", 0)
    })

@app.get("/{path:path}")
async def get_static(path: str):
    file_path = _safe_static_path(path)
    if file_path is None:
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(file_path)

if __name__ == "__main__":
    import sys
    port = 8086
    if "--port" in sys.argv:
        port = int(sys.argv[sys.argv.index("--port") + 1])
    uvicorn.run(app, host="0.0.0.0", port=port)
