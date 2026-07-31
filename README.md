# MJ AI: Advanced Autonomous Research & Hybrid Reasoning Engine

MJ AI is a state-of-the-art autonomous research agent and intelligence platform. It fuses high-speed cloud inference with a local PyTorch consensus stack, dynamic vector memory recall, and real-time scrapers to deliver deep factual synthesis. 

The user experience features a premium glassmorphic interface inspired by campaign-oriented metrics dashboard layouts, operating in a highly-readable Light Theme.

---

## 🛠 System Architecture

MJ AI operates on a multi-tier hybrid intelligence design:

```
                  ┌────────────────────────────────────────┐
                  │          React Frontend (Vite)         │
                  └───────────────────┬────────────────────┘
                                      │ (REST APIs)
                  ┌───────────────────▼────────────────────┐
                  │            FastAPI Server              │
                  └───────────────────┬────────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              │                       │                       │
     ┌────────▼────────┐     ┌────────▼────────┐     ┌────────▼────────┐
     │   Groq Engine   │     │  Memory Vector  │     │  Local Ensemble │
     │  (Llama 3.3 70B)│     │  (JSON / Mongo) │     │ (DistilBERT/MLP)│
     └─────────────────┘     └─────────────────┘     └─────────────────┘
```

1. **Orchestration & Reasoning (Cloud)**: Executes agent loops, multi-agent debates, and final responses exclusively via **Groq** (`llama-3.3-70b-versatile` / `llama3-8b-8192`) for ultra-low latency.
2. **Context Memory (RAG)**: A vector-like semantic memory space powered by a local JSON fallback (`memory.json`) or MongoDB.
3. **Local Consensus Engine (Edge)**: DistilBERT embeddings connected to a parallel **PyTorch Multi-Layer Perceptron (MLP)** and **Scikit-Learn Random Forest Classifier** to compute consensus confidence values on local memories.

---

## 📂 Repository Structure

```tree
MJ_AI/
├── backend/                  # Core Service Layer & Neural Engines
│   ├── models/               # Serialized neural weights (model.pth)
│   ├── server.py             # FastAPI REST Server
│   ├── main.py               # Autonomous reasoning agent loop
│   ├── memory.py             # Dual-mode local JSON / MongoDB driver
│   ├── learning.py           # DistilBERT & MLP training script
│   ├── train_mcq.py          # MCQ dataset pipeline & classifier trainer
│   └── *.py                  # Mathematical engines & scrapers
│
├── frontend/                 # Interactive SPA Client
│   ├── src/
│   │   ├── App.jsx           # App layout & Framer Motion transitions
│   │   └── index.css         # Glassmorphic light theme design system
│   ├── vite.config.js        # Build configuration & proxy tables
│   └── index.html            # Entry layout template
│
├── .env                      # API Credentials (ignored)
├── .gitignore                # System and Cache Exclusions
└── requirements.txt          # Python Package Manifest
```

---

## ⚡ Technical Stack

* **Frontend SPA**: React (v18), Vite, Framer Motion (micro-interactions), Chart.js (analytics rendering), marked (markdown cells).
* **AI & Classifiers**: Groq API, PyTorch (Deep Neural Head), Transformers (DistilBERT tokenizers), Scikit-Learn (Random Forest & K-Means clustering).
* **Research Stack**: BeautifulSoup4, DuckDuckGo Scraper, SymPy Algebraic Core.

---

## 🚀 Getting Started

### 1. Environment Configurations
Copy [`.env.example`](.env.example) to `.env` at the root of the workspace directory and fill in real values:
```env
GROQ_API_KEY=gsk_your_api_key_here
OPENROUTER_API_KEY=sk-or-v1-your_api_key_here
MJ_API_TOKENS=change-me-to-a-random-token
```
`MJ_API_TOKENS` is required - every `/api/*` route rejects requests until it's set (see
[`backend/auth.py`](backend/auth.py)). Generate a strong token with:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Backend Initialization
Set up your Python virtual environment (Python 3.10+ recommended) and run:
```bash
# Install required libraries
pip install -r requirements.txt

# Launch FastAPI web engine
python backend/server.py
```
*The API server will spin up on `http://127.0.0.1:8086`.*

### 3. Frontend Initialization
In a separate terminal shell, navigate to the `frontend/` directory. Copy
[`frontend/.env.example`](frontend/.env.example) to `frontend/.env` and set
`VITE_MJ_API_TOKEN` to the **same token** you put in `MJ_API_TOKENS` above:
```bash
# Install node packages
npm install

# Run hot-reloading development server
npm run dev
```
*The client dashboard will be served at `http://localhost:3000`.*

### 4. MCQ Dataset Training
To populate your local memory with the custom Aptitude, Quantitative, and Reasoning MCQ datasets and retrain the edge classifiers:
```bash
python backend/train_mcq.py
```

---

## ✨ Design & Aesthetic Philosophy

- **Glassmorphic Layout**: Uses translucent backdrops (`backdrop-filter`) with fine border separators to isolate workspace elements.
- **Campaign-Style Metrics**: Displays vector memory capacity, persistence, and classification health using card deck styles inspired by crowdfunding platforms.
- **Framer Motion Transitions**: Smooth entry animations on card grids, tab switches, and chat bubbles.
- **Micro-Animations**: Uses dynamic scale adjustments on clicks and CSS pulse elements on active status gauges.

---

## 💡 Capabilities & User Stories

### 🌐 1. Autonomous Web Research & Synthesis
* **The Story**: A user asks, *"Who is the current CEO of Microsoft and what is their background?"*
* **Under the Hood**:
  1. The agent parses the query and realizes it needs real-time internet data.
  2. It generates a `[SEARCH: current CEO of Microsoft]` command. The web scraper searches DuckDuckGo and fetches search snippet objects.
  3. The agent reads the search results, generates a secondary `[FETCH: URL]` command to scrape the official biography page, extracting clean text.
  4. The Groq reasoning core synthesizes the scraped text and returns a clean, detailed biography.

### 🧠 2. Semantic Memory Checkpointing
* **The Story**: During a session, the user asks to summarize a complex topic: *"Summarize the core arguments of the security audit."*
* **Under the Hood**:
  1. The agent compiles a summary block wrapped in programmatic tags: `[MEM_SUMMARY: ...]`.
  2. The system detects the summary payload and outputs a confirmation prompt: *"Do you want me to save this in memory for future reference? (Yes/No)"*
  3. If the user clicks **Confirm**, a confetti wave triggers, and the summary is parsed and stored inside `memory.json` as a `verified-persistent` record, becoming part of the agent's long-term retrieval context.

### 🔬 3. Edge-Consensus Classifier Training (MCQ Mode)
* **The Story**: Aptitude questions from local JSON files are imported into the system.
* **Under the Hood**:
  1. The dataset pipeline loads files from `backend/mcq_data` and stores them in the local memory layer.
  2. The system triggers the local training loop: it computes DistilBERT embeddings for all inputs, clusters them using K-Means, and fits a PyTorch MLP neural network along with a Scikit-Learn Random Forest.
  3. The next time the user asks a math/logic question that matches the semantic space of the dataset, the local PyTorch + Random Forest heads achieve a consensus score and serve the cached answer in less than 20ms, bypassing cloud inference.

### 🛡️ 4. Automated Security Audits (RedSage Specialist)
* **The Story**: The user clicks **Run RedSage Scan** to review the active project codebase.
* **Under the Hood**:
  1. The request routes to the `RedSageAgent` inside the backend.
  2. The agent scans the filesystem configurations, dependencies, and code patterns for security concerns (e.g. CWE-94, CWE-502).
  3. It compiles a detailed markdown report, saves it in the `frontend` folder, and returns a direct link for the user to view the audit findings in a new browser tab.

