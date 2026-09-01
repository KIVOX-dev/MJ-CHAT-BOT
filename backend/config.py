import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
# Host of the Pinecone index used for semantic memory search (see memory.py).
# Connecting by host skips a name->host lookup on every request. Leave blank
# to disable semantic search - find_relevant() falls back to keyword search.
PINECONE_INDEX_HOST = os.getenv("PINECONE_INDEX_HOST", "")
PINECONE_NAMESPACE = os.getenv("PINECONE_NAMESPACE", "mj-memory")
MONGO_URI = os.getenv("MONGO_URI", "")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(BASE_DIR, "memory.json")

# Canonical filename for the trained ensemble checkpoint (see learning.py's
# save()/load()). Single source of truth so the save path and the load path
# can never drift apart the way models/model.pth (a stale, structurally
# incompatible checkpoint from an older fc1/fc2 architecture) and the
# ensemble_v6.pth the loader actually looked for once did. Bump this if the
# EnsembleBrain architecture changes again in a way that makes old
# checkpoints incompatible.
MODEL_FILENAME = os.getenv("MJ_MODEL_FILENAME", "ensemble_v6.pth")

# Model Hyperparameters
CONFIDENCE_THRESHOLD = 0.90 # Minimum confidence to trust internal model summary
TRAIN_INTERVAL = 5           # Train model every N new memories


def _parse_api_tokens(raw: str) -> dict:
    """
    Parses MJ_API_TOKENS as a comma-separated list of `token` or
    `token:identity` pairs into {token: identity}. A bare token with no
    ":identity" is assigned the identity "default", so a single-operator
    deployment can set one token and get exactly today's single-owner
    behavior back.
    """
    tokens = {}
    for pair in raw.split(","):
        pair = pair.strip()
        if not pair:
            continue
        token, _, identity = pair.partition(":")
        token = token.strip()
        identity = identity.strip() or "default"
        if token:
            tokens[token] = identity
    return tokens


# Maps bearer token -> identity name. Every /api/* route requires a token
# from this map (see auth.py). Configure via MJ_API_TOKENS, e.g.:
#   MJ_API_TOKENS=changeme-token-1:alice,changeme-token-2:bob
API_TOKENS = _parse_api_tokens(os.getenv("MJ_API_TOKENS", ""))

# Rate limits for POST /api/chat (see server.py). Format is a `limits`
# library string, e.g. "60/minute". The authenticated tier applies once a
# valid bearer token resolves to an identity; the anonymous tier is the
# per-IP fallback used by the shared default_limits baseline.
CHAT_RATE_LIMIT_AUTHENTICATED = os.getenv("MJ_CHAT_RATE_LIMIT_AUTHENTICATED", "60/minute")
CHAT_RATE_LIMIT_ANONYMOUS = os.getenv("MJ_CHAT_RATE_LIMIT_ANONYMOUS", "10/minute")
