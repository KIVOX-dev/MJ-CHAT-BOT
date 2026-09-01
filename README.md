# MJ AI

MJ AI is a self-hosted research assistant that pairs a FastAPI backend with a React frontend. It answers questions by routing them through a small local classifier first, falling back to live web research and cloud LLM reasoning (Groq) when the query calls for it, and it remembers what it learns across sessions — first as exact-match lookups, and now as semantic recall backed by a Pinecone vector index.

It also ships a lightweight security-audit tool (RedSage) that scans the project's own codebase on demand and returns a findings report in the UI.

## How a request is handled

```
                  ┌──────────────────────────────────┐
                  │        React Frontend (Vite)      │
                  └──────────────────┬─────────────────┘
                                     │ REST, bearer-token auth
                  ┌──────────────────▼─────────────────┐
                  │            FastAPI Server           │
                  └──────────────────┬─────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
┌───────▼────────┐         ┌─────────▼─────────┐         ┌────────▼────────┐
│  Local Ensemble │         │   Memory Layer     │         │  Groq Reasoning  │
│ (DistilBERT +   │         │ (Mongo/local JSON   │         │  + Web Research  │
│  MLP + Forest)  │         │  + Pinecone vector) │         │  (search/fetch)  │
└─────────────────┘         └─────────────────────┘         └──────────────────┘
```

A query is handled in roughly this order:

1. **Local ensemble check.** If a DistilBERT-embedded classifier (an MLP plus a Random Forest, trained on prior conversations) is confident enough, it answers directly — no network call, typically under 20ms.
2. **Memory recall.** Relevant past exchanges are pulled in as context: semantically via Pinecone when it's configured, or by keyword match against MongoDB / a local `memory.json` file otherwise.
3. **Reasoning loop.** Groq (`llama-3.3-70b-versatile`, with an 8B fallback) generates the response, issuing `[SEARCH: ...]` / `[FETCH: ...]` commands mid-conversation when it needs current information — DuckDuckGo and Wikipedia back the search step, BeautifulSoup handles page extraction.
4. **Write-back.** The exchange is stored for future recall, and every few turns the local classifier retrains on what's accumulated.

## Repository layout

```
.
├── backend/
│   ├── server.py        FastAPI app: routes, auth, rate limiting, static hosting
│   ├── main.py           Orchestrates the request pipeline described above
│   ├── memory.py         Mongo / local-JSON / Pinecone-backed memory layer
│   ├── learning.py       DistilBERT + PyTorch MLP + scikit-learn ensemble
│   ├── reasoning.py       Groq reasoning loop, search/fetch command parsing
│   ├── redsage.py        On-demand codebase security audit
│   ├── auth.py           Bearer-token identity resolution
│   ├── config.py         Environment variable loading
│   └── models/            Serialized checkpoints (gitignored; trained locally)
│
├── frontend/
│   ├── src/App.jsx        Chat UI, session list, metrics dashboard
│   └── vite.config.js     Dev server + API proxy
│
├── vercel.json            Frontend-only Vercel service definition
├── requirements.txt       Backend dependencies
└── .env.example           Documents every environment variable the app reads
```

## Running it locally

**1. Configure environment variables.** Copy [`.env.example`](.env.example) to `.env` at the repo root:

```bash
GROQ_API_KEY=gsk_your_key_here
MJ_API_TOKENS=change-me-to-a-random-token
```

`MJ_API_TOKENS` is required — every `/api/*` route returns 503 until it's set (see [`backend/auth.py`](backend/auth.py)). Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`MONGO_URI` and `PINECONE_API_KEY`/`PINECONE_INDEX_HOST` are optional — omitting them falls back to a local `memory.json` file and keyword-only recall, respectively.

**2. Start the backend** (Python 3.11–3.13 recommended):

```bash
pip install -r requirements.txt
python backend/server.py
```

Serves on `http://127.0.0.1:8086`.

**3. Start the frontend**, in a second terminal. Copy [`frontend/.env.example`](frontend/.env.example) to `frontend/.env` and set `VITE_MJ_API_TOKEN` to the same value as `MJ_API_TOKENS`:

```bash
cd frontend
npm install
npm run dev
```

Serves on `http://localhost:3000`, proxying `/api` to the backend.

**4. (Optional) Train the classifier** on the bundled aptitude/reasoning MCQ dataset:

```bash
python backend/train_mcq.py
```

## Deployment

The frontend and backend deploy independently.

- **Frontend → Vercel.** [`vercel.json`](vercel.json) declares a single `frontend` service so Vercel doesn't try to auto-detect the Python backend as a second service. Set `VITE_MJ_API_TOKEN` as a Vercel environment variable — it's baked into the build at compile time.
- **Backend → Render** (or any host that runs a persistent process — the training loop and in-memory state don't fit a serverless model). Build command `pip install -r requirements.txt`; start command `cd backend && uvicorn server:app --host 0.0.0.0 --port $PORT`. Set the backend's environment variables (`MJ_API_TOKENS`, provider keys, `MONGO_URI`, `PINECONE_*`) in the host's dashboard. Without `MONGO_URI`, memory falls back to a local file on the host's filesystem, which will not survive a redeploy.

## What it can do

**Web research.** Given "Who is the current CEO of Microsoft, and what's their background?", the agent issues a search command, reads the results, follows up with a fetch of the relevant page, and synthesizes a sourced answer — rather than guessing from training data alone.

**Semantic memory.** Ask something worded differently from how it was originally discussed, and `memory.find_relevant()` still surfaces it: records are embedded and searched by meaning via Pinecone, not just exact substring match. Confirming a summary (`[MEM_SUMMARY: ...]`, then a "yes") promotes it to a `verified-persistent` record that future queries retrieve first.

**Fast local answers.** Once the ensemble classifier has enough training data for a topic, it can answer without a cloud round-trip at all — the local MLP and Random Forest heads reach consensus and serve directly.

**Security self-audits.** Asking for a "security audit" or "RedSage scan" runs a static review of the codebase and returns a markdown report, linked from the chat response.
