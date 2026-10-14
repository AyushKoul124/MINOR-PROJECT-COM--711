# AI-Driven Social Media Audience Intelligence Framework
## Academic Research Prototype | 7th Semester CSE Minor Project
### Reference Hardware: NVIDIA GTX 1650 Ti (4GB VRAM) | 16GB RAM | 1TB SSD | Offline-First

---

> **Academic Research Testbed Disclaimer:**  
> This system is an undergraduate academic proof-of-concept (PoC) and research testbed developed for a 7th-semester CSE minor project. The National Technical Research Organisation (NTRO) is the origin of the public problem statement **only**. This software is **not** an operational intelligence system, is **not** deployed by NTRO or any defense agency, and does **not** claim operational intelligence capability.

---

## 1. Quickstart & Developer Runbook

### Step 1: Start PostgreSQL (pgvector) & Redis
Make sure Docker Desktop is running, then start the containerized databases:
```bash
docker compose up -d
```
Verify that `postgres` and `redis` are healthy:
```bash
docker compose ps
```

### Step 2: Set Up Python Environment
Create a Python 3.11+ virtual environment and install dependencies:
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Install dependencies:
pip install -r requirements.txt
```

### Step 3: Run Database Migrations
Initialize the schema and enable pgvector:
```bash
alembic upgrade head
```

### Step 4: Run the Offline Viva Demo Replay (Zero Internet Required)
Populate the database with sanitized historical seed data without touching the live Telegram API:
```bash
python -m ingestion_a.backfill --offline
```

### Step 5: Start Local Ollama for RAG (Air-Gapped)
In a separate terminal, ensure Ollama is serving the offline reference model:
```bash
ollama run llama3.2:3b
```

### Step 6: Start FastAPI Backend
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger API documentation: [http://localhost:8000/docs](http://localhost:8000/docs)

### Step 7: Start React Bento Dashboard
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## 2. Monitored Target Pool & Rate Limiting Math

The system tracks **30 curated public channels** around Indian space, defense, and technology policy (`config/channels.yaml`).

To prevent Telegram MTProto `FloodWaitError` without compromising data freshness:
$$\text{Polling Cadence} = \frac{900 \text{ seconds (15-minute window)}}{30 \text{ channels}} = \mathbf{30.0 \text{ seconds per channel}}$$

* Celery Beat executes a **continuous staggered polling schedule**: 1 channel is polled every 30 seconds with 2–5s randomized jitter.
* The global request velocity is steady at **$\sim 2$ requests/minute**, mimicking organic human reading.
* Ingestion concurrency is pinned strictly to `--concurrency=1` to protect SQLite `.session` files from multi-process write locks.

---

## 3. Hardware Profile & Sequential VRAM Pipeline

* **Reference Development Rig:** NVIDIA GeForce GTX 1650 Ti (4 GB GDDR6 VRAM), 16 GB DDR4 RAM, 1 TB SSD.
* **4GB VRAM Invariant:** Transformer models cannot be loaded concurrently without causing CUDA Out-Of-Memory (OOM) crashes.
* **Sequential Execution:** The Celery worker runs inference in sequential pipeline stages:
  1. `twitter-xlm-roberta-base-sentiment` batch $\rightarrow$ `torch.cuda.empty_cache()`
  2. `roberta-base-go_emotions` batch $\rightarrow$ `torch.cuda.empty_cache()`
  3. `distilbart-mnli-12-3` stance batch $\rightarrow$ `torch.cuda.empty_cache()`
  4. `paraphrase-multilingual-MiniLM-L12-v2` embeddings $\rightarrow$ `torch.cuda.empty_cache()`
* **Demo Timing:** The "Run Analysis Now" trigger completes in **15–25 seconds** on the reference GPU for a capped batch of $\le 50$ seed posts.

---

## 4. Key Documentation Index

* [PROJECT_BRIEF.md](PROJECT_BRIEF.md) ([PDF](PROJECT_BRIEF.pdf)) — Canonical project specification & scope.
* [ARCHITECTURE.md](ARCHITECTURE.md) ([PDF](ARCHITECTURE.pdf)) — Architectural specification & mathematical limits.
* [CURSOR_BRIEF.md](CURSOR_BRIEF.md) ([PDF](CURSOR_BRIEF.pdf)) — AI prompting & engineering reference.
* [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) ([PDF](IMPLEMENTATION_PLAN.pdf)) — 15-week implementation roadmap.
* [.cursorrules](.cursorrules) — Cursor IDE automated rule enforcement.
