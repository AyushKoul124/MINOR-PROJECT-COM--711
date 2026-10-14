# Architecture Specification & Engineering Reference (Academic Prototype)
## AI-Driven Social Media Audience Intelligence Framework
### Academic Research Prototype | 7th Semester CSE Minor Project | Team of 4 (P1–P4)
### Reference Hardware: NVIDIA GTX 1650 Ti (4GB VRAM) | 16GB RAM | 1TB SSD | Offline-First (v4.8)

---

> **Document Status:** Canonical Living Architecture Document (v4.8 — Hardware Realism, Sequential VRAM Pipeline & Offline-First Product Rule).  
> **System Classification:** Academic Proof-of-Concept (PoC) / Research Testbed. **NTRO is the public problem-statement source only** — this is not an operational intelligence deployment, is not deployed by any defense agency, and does not claim operational intelligence capability.  
> **Audience:** Core Engineering Team (P1–P4), Faculty Reviewers, and Viva Defense Examiners.

---

## 1. System Overview & Problem Statement

This system is a **student academic prototype** that monitors **30 curated public Telegram broadcast channels** (and associated public discussion threads), runs five analytical agents (A–E), and surfaces findings on an interactive Bento Grid dashboard plus a grounded retrieval interface over **agent summaries**.

It is motivated by public audience-intelligence problem statements (including an NTRO-originated public statement used for the minor project). It does **not** claim NTRO operational capability or enterprise SOCMINT status.

### The Cardinal Product Rule (Offline-First Invariant)
**"Build the offline demo as the primary product; treat live Telegram collection and cloud LLMs as optional depth."**  
Campus Wi-Fi drops, Telegram FloodWait rate limits, and missing API keys are fatal viva failure modes. The primary deliverable is a deterministic, air-gapped seed data replay script (`backfill.py --offline` / SQL seed) and local LLM inference via Ollama (`llama3.2:3b`). Live Pyrofork MTProto ingestion is an optional depth feature demonstrated only if the campus network allows.

### Core Analytical Capabilities:
1. **Longitudinal Sentiment & Stance Trajectories:** Measuring population-level emotional resonance and policy stance over time with off-the-shelf pre-trained transformers, without conflating emotion with ideological alignment.
2. **Emergent Topic Velocity & Acceleration:** Identifying accelerating narratives before volume peaks, distinguishing organic interest from coordinated amplification.
3. **Coordinated Inauthentic Behavior (CIB) Screening:** Detecting topological and temporal synchrony across broadcasting entities and active participant clusters using an intuitive 3-signal anomaly heuristic.
4. **Grounded Query over Agent Summaries:** An analyst query terminal that retrieves the system's own 2–4 sentence agent summaries and **refuses** when cosine distance is too high ($\ge 0.65$) — a disciplined retrieve-and-refuse mechanism, not a hallucination-free oracle.

---

## 2. Multi-Agent Pipeline Topology

The platform rejects monolithic processing in favor of **five independently invocable analytical agents (A–E)** coordinated by a lightweight orchestrator, backed by PostgreSQL 16 + pgvector and Redis.

```
                  ┌──────────────────────────────────────────────┐
                  │          Public Telegram Channels            │
                  │              (30 Curated Channels)           │
                  └──────┬───────────────────────┬───────────────┘
                         │ MTProto / Pyrofork     │ Desktop Export (JSON)
                         ▼                        ▼
                  ┌──────────────────────────────────────────────┐
                  │       Component A: Ingestion Agent           │
                  │   - Offline seed replay (PRIMARY DEMO PATH)  │
                  │   - Desktop JSON import (--import-json)      │
                  │   - 15m polling + random jitter (5–15s)      │
                  │   - Celery concurrency pinned (--concurrency=1)│
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │          PostgreSQL 16 Storage Layer         │
                  │   - raw_posts (immutable after write)        │
                  │   - raw_authors (append-only snapshots)      │
                  │   - pgvector (384-dim HNSW cosine index)     │
                  └──────┬───────────────┬───────────────┬───────┘
                         │               │               │
     ┌───────────────────┘               │               └───────────────────┐
     │ (Sequential Row Batch)            │ (Sliding time window)             │ (Sliding time window)
     ▼                                   ▼                                   ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│ Component B: Sentiment  │ │ Component D: Trends     │ │ Component E: Network    │
│ - xlm-roberta sentiment │ │ - BERTopic + HDBSCAN    │ │ - Directed Graph Build  │
│ - GoEmotions (Ekman map)│ │ - One MiniLM embedder   │ │ - Louvain Projection    │
│ - DistilBART NLI stance │ │ - Velocity & Accel      │ │ - Betweenness Sort      │
│ - Sequential GPU cache  │ │ - Cap 500 docs / run    │ │ - 3-Signal CIB Anomaly  │
│ - Sarcasm flag (no flip)│ └────────────┬────────────┘ └────────────┬────────────┘
└────────────┬────────────┘              │                           │
             │              ┌────────────┴────────────┐              │
             │              │ Component C: Demographic│              │
             │              │ (2-tier audience parse) │              │
             │              │ - k-Anonymity Guard ≥50 │              │
             │              └────────────┬────────────┘              │
             │                           │                           │
             └───────────────────┬───────┴───────────────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────────────────────┐
                  │           Orchestrator & RAG Layer           │
                  │   - 2–4 Sentence Agent Summary Embeddings    │
                  │   - Temporal Metadata Context Packaging      │
                  │   - Distance Cutoff (< 0.65) Short-Circuit   │
                  │   - Dual LLM: Ollama (viva) / Groq (cloud)   │
                  │   - rag_query_log Mandatory Audit Trail      │
                  │   - "Run Analysis Now" (capped <=50 posts)   │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │         FastAPI ↔ React 18 Dashboard         │
                  │   - 7 Core Bento Grid Views                  │
                  │   - Edge-induced Subgraph Cap (Top 500)      │
                  │   - Uncertainty-Aware UX & Confidence Flags  │
                  └──────────────────────────────────────────────┘
```

---

## 3. Honest Self-Assessment, Hardware Realism & Limitations

In intelligence systems engineering, unstated assumptions and overstated model capabilities are critical vulnerabilities. The following subsections document the explicit mathematical trade-offs, empirical boundaries, and deliberate design compromises embedded in the framework.

### 3.1 Hardware Budget & Sequential VRAM Pipeline Strategy
* **Target Reference Dev & Demo Machine:**
  - **GPU:** NVIDIA GeForce GTX 1650 Ti Mobile (4 GB GDDR6 VRAM)
  - **System Memory:** 16 GB DDR4 RAM
  - **Storage:** 1 TB NVMe SSD + 1 TB HDD
  - **OS:** Windows 11 / WSL2 / Docker Desktop
* **Teammate Minimum Fallback Spec:** 8–16 GB RAM, Quad-Core CPU, CPU-only fallback using quantized models / seed replay.
* **VRAM Memory Footprint Reality Check (4 GB Budget):**
  - `cardiffnlp/twitter-xlm-roberta-base-sentiment` : ~1.1 GB
  - `SamLowe/roberta-base-go_emotions`              : ~500 MB
  - `valhalla/distilbart-mnli-12-3` (stance)        : ~260 MB  (replaces 1.6 GB `bart-large`)
  - `paraphrase-multilingual-MiniLM-L12-v2` (embed)  : ~470 MB
  - Ollama (`llama3.2:3b` 4-bit quantized)          : ~2.0 GB
  - Postgres + Redis + Celery + FastAPI + React   : ~2.5–3.5 GB System RAM
  - **Co-resident Total:** >4.3 GB VRAM $\rightarrow$ **Exceeds 4 GB VRAM if loaded concurrently!**
* **Strict Invariant — Sequential GPU Execution Pipeline:**
  - To prevent catastrophic CUDA OOM crashes on 4 GB VRAM cards, the worker **never** holds all models resident on the GPU at once.
  - Ingestion and preprocessing stage the batch. Component B executes sequentially:
    1. Run XLM-RoBERTa sentiment batch $\rightarrow$ invoke `torch.cuda.empty_cache()`
    2. Run GoEmotions emotion batch $\rightarrow$ invoke `torch.cuda.empty_cache()`
    3. Run DistilBART stance batch $\rightarrow$ invoke `torch.cuda.empty_cache()`
    4. Run MiniLM embeddings for BERTopic $\rightarrow$ invoke `torch.cuda.empty_cache()`
  - Ollama runs in an independent system process (`ollama serve`). On 4 GB hardware, Ollama automatically shares VRAM or offloads layers to system RAM.
* **Demo Timing Calibration:**
  - The "Run Analysis Now" viva trigger finishes in **15–25 seconds on the reference GTX 1650 Ti** ONLY for a capped batch of **$\le 50$ seed posts**.
  - Historical bulk analysis runs asynchronously in background via Celery Beat, not instantaneously.

### 3.2 Stance Threshold Calibration & DistilBART Runtime Default
Stance detection in Component B is operationalized using Natural Language Inference (Zero-Shot NLI via `valhalla/distilbart-mnli-12-3`) rather than a supervised classifier, evaluating posts against target hypotheses (*"This text expresses support for {topic}"* vs. *"This text expresses opposition to {topic}"*).
- **Runtime Default:** `valhalla/distilbart-mnli-12-3` (~260 MB, 6x smaller and 3x faster than BART-large).
- **Evaluated Baseline:** `facebook/bart-large-mnli` (~1.6 GB) is evaluated offline in the report for benchmark comparison, but is excluded from the default live runtime to protect the 4 GB VRAM budget.
- **Threshold Calibration:** The classification boundary enforces a hard threshold of **0.60**: if neither hypothesis attains $\ge 0.60$ entailment probability, or if contradictory signals emerge, the pipeline assigns `'neutral'` or `'unclear'` rather than forcing a binary categorization.
- Setting the decision boundary at 0.60 explicitly trades recall for precision: weakly committed posts fall into `'neutral'`, ensuring that posts labeled `'supportive'` or `'against'` possess high-confidence entailment evidence.

### 3.3 Sarcasm Detection Ceiling & Advisory Uncertainty Bounds
Linguistic, syntactic, and emoji-based sarcasm heuristics (in `sentiment_b/sarcasm.py` via valence-emoji incongruity, intensifier contradiction, and punctuation clustering) have an empirical F1 ceiling typically reported between **50% and 65% in the literature** (e.g., SemEval-2018 Task 3 irony baselines; SARC 2.0 benchmarks; Swami et al., 2018). In South Asian multi-dialectal and code-mixed environments (English + Romanized Hinglish), sarcasm depends heavily on unstated cultural context.

Acknowledging this empirical ceiling, the framework treats sarcasm detection **strictly as an advisory uncertainty flag (`sarcasm_flag = TRUE`) and confidence penalizer, never as an automated valence inverter**. The pipeline never flips a positive classification to negative simply because a sarcastic emoji was detected. Flagged posts are marked with a visible "Lower Confidence / Sarcasm Flagged" warning in the UI, preserving aggregate transparency without introducing compounding error.

### 3.4 Operational Security Posture & Threat Model Demarcation
The security architecture is designed and bounded as an **academic Proof-of-Concept (PoC) and evaluation testbed**, optimized for developer ergonomics, multi-agent orchestration demonstration, and local reproducibility during viva defense. Access control relies on HTTP Basic Authentication over FastAPI, local `.env` configuration, internal Docker bridge networks, and strict SQLite session single-process concurrency controls (`--concurrency=1` on Celery) to prevent MTProto `.session` file corruption.

This architecture explicitly **does not represent a hardened, production-grade SOCMINT deployment**. Sovereign intelligence systems require mutual TLS (mTLS), Hardware Security Modules (HSM), fine-grained RBAC/ABAC, and air-gapped egress proxies.

### 3.5 3-Signal Arithmetic Mean for CIB Screening
Rather than asserting unvalidated, pseudo-precise statistical regression weights across an unannotated Telegram domain, Component E composites three transparent, intuitive heuristic sub-signals into an unweighted arithmetic mean:
$$\text{anomaly\_score} = \frac{s_1 + s_2 + s_3}{N_{\text{available}}}$$
where:
- $s_1$: **Posting Synchrony** — accounts posting within unusually tight time windows relative to one another (using platform `posted_at`).
- $s_2$: **Account Age vs. Volume** — young accounts generating disproportionately high message volumes.
- $s_3$: **Content Duplication** — near-duplicate message text via TF-IDF cosine similarity.

If $\text{anomaly\_score} \ge 0.70$, the entity is flagged with `coordination_signal = TRUE`. This formulation is robust, transparent to examiners, dynamically averages over available signals, and avoids inventing complex weight parameters that have no ground-truth empirical calibration on Telegram data. It is an **advisory screening indicator**, never a legal verdict.

---

## 4. Component Technical Specifications

### Component A: Ingestion Agent
- **Primary Product Deliverable (Offline Viva Path):** Standalone replay script (`ingestion_a/backfill.py --offline`) loads historical posts from `scripts/seed_demo_data.sql` with normalized timestamps into PostgreSQL. **The viva must succeed on this path with zero internet connectivity.**
- **Live MTProto Driver:** Pyrofork wrapped in `BaseIngestionAdapter`. Staggered continuous polling: 1 channel polled every 30 seconds with 2–5s randomized jitter across a 15-minute cycle ($30 \times 30\text{s} = 900\text{s}$), maintaining a global rate of $\sim 2$ requests/min to eliminate Telegram API FloodWait. Celery worker concurrency locked strictly to `--concurrency=1` to prevent SQLite `.session` database lock contention.
- **Telegram Desktop JSON Import:** Script (`ingestion_a/import_exported.py --import-json <path>`) parses Telegram Desktop JSON exports into `raw_posts` with `processing_status = 'pending'`, providing historical depth without API dependencies.

### Component B: Sentiment, Emotion & Stance Agent
- **Off-the-Shelf Pre-trained Transformers (No Custom Training Claimed):**
  - **Sentiment (all text):** `cardiffnlp/twitter-xlm-roberta-base-sentiment` — multilingual sentiment classifier (positive/negative/neutral), pre-trained on 198M tweets across 8 languages. Handles English and Hinglish (Roman-script code-mixed Hindi-English) without routing.
  - **Emotion (English/Hinglish):** `SamLowe/roberta-base-go_emotions` — 28-class emotion classifier mapped to 7 core dimensions (`joy`, `anger`, `sadness`, `disgust`, `surprise`, `neutral`, `fear`).
  - **Stance (all text):** Zero-Shot NLI via **`valhalla/distilbart-mnli-12-3` (runtime default locked)** against target hypotheses. Hard 0.60 threshold.
- **Sequential GPU Execution:** Enforces `torch.cuda.empty_cache()` between pipeline stages to guarantee execution within 4 GB VRAM.
- **No Devanagari Regex Language Router:** Target channels produce English and Romanized Hinglish content. Multilingual XLM-RoBERTa handles both natively.
- **Sarcasm Flag:** Advisory penalty only (`sarcasm_flag = TRUE`). Never inverts sentiment polarity.

### Component C: Demographic Agent
- **Operational Boundary:** Telegram subscriber rosters are strictly private. Profiling operates across two observable heuristic tiers:
  1. *Broadcast Tier:* Channel-level language, timezone diurnal posting rhythms, and description keywords.
  2. *Audience Tier:* Inferred distributions derived strictly from active participants in linked public discussion groups and comment threads.
- **k-Anonymity Cluster Guard:** Aggregate-only outputs. Any cluster with account count $< 50$ is flagged `below_threshold: true` and greyed out in the UI. UI title: **Audience aggregates (inferred)** — coarse bio/keyword heuristic, not census demographics.

### Component D: Trend & Topic Agent
- **Model:** BERTopic utilizing `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions, 50+ languages). Single shared embedder for both BERTopic and RAG.
- **Sparse Corpus Tuning:** Calibrated to `min_topic_size = 3` and `topic_model.reduce_outliers(..., strategy="c-tf-idf")`. **Input documents capped at 500 per run** to eliminate memory spikes.
- **Temporal Metric:** Ranks topics by velocity ($v = \frac{\Delta \text{posts}}{\Delta t}$) and acceleration ($a = \frac{\Delta v}{\Delta t}$) calculated strictly using `posted_at` timestamps (never `ingested_at`).

### Component E: Network & CIB Agent
- **Graph Construction:** Directed multigraph of interactions (`forward`, `reply`, `mention`) stored in `network_edges_e`.
- **Community Projection:** Directed graph is projected into an undirected representation (`G.to_undirected(as_view=False)`) prior to executing Louvain modularity (`python-louvain`, imported as `import community`).
- **Canvas Protection & Edge Induction:** Centrality sorting prioritizes Betweenness Centrality. Graph payload is capped at top 500 nodes. Edges are strictly filtered to the induced subgraph.
- **3-Signal CIB Screening:** Heuristic average of posting synchrony ($s_1$), age-to-volume ratio ($s_2$), and content duplication ($s_3$). Flagged if score $\ge 0.70$.

---

## 5. Grounded Retrieval (RAG) — Retrieve, Refuse, One LLM Pass

The query layer retrieves **agent summaries** (not noisy raw posts) and generates an answer with citations. It is a pragmatic retrieve-and-refuse pipeline with a single structured LLM pass, not a published CRAG/Self-RAG implementation or hallucination-free oracle.

- **Offline Viva Default:** Ollama `llama3.2:3b` on `localhost:11434` (zero internet dependency).
- **Optional Development:** Groq `llama-3.3-70b-versatile` when an API key is available. (No unverified "98% grounding accuracy" marketing claims).
- Configured via `LLM_PROVIDER=ollama|groq|openai` in `.env`.

### 5.1 Pipeline Topology

```
                              Analyst Query
                                    │
                                    ▼
                 [ Embed Query: MiniLM-L12-v2 (384-dim) ]
                                    │
                                    ▼
       [ Tier 0: Vector Search: pgvector HNSW Cosine Distance ]
           SELECT ... WHERE (embedding <=> :q) < 0.65 LIMIT 5
                                    │
          ┌─────────────────────────┴─────────────────────────┐
          ▼ (Distance ≥ 0.65)                                 ▼ (Distance < 0.65)
┌───────────────────────────┐                       ┌───────────────────────────┐
│ Tier 0 Hard Rejection     │                       │ Candidate Chunks (Top-5)  │
│ "Insufficient data..."    │                       └─────────────┬─────────────┘
│ (Zero LLM invocation)     │                                     │
└───────────────────────────┘                                     ▼
                                                    ┌───────────────────────────┐
                                                    │ Tier 1: Temporal filter   │
                                                    │ • Window vs query time    │
                                                    │ • CORRECT / AMBIGUOUS /   │
                                                    │   INSUFFICIENT            │
                                                    └─────────────┬─────────────┘
                                                                  │
          ┌───────────────────────────────────────────────────────┴───────────────────────┐
          ▼ (Relevance = INSUFFICIENT)                                                    ▼ (Relevance = CORRECT / AMBIGUOUS)
┌───────────────────────────────────────┐                               ┌───────────────────────────────────────┐
│ Deterministic fallback                │                               │ Tier 2: One structured LLM call       │
│ "No verified findings match..."       │                               │ • answer                              │
│                                       │                               │ • cited_document_ids: [DOC_1, ...]    │
└───────────────────────────────────────┘                               │ • is_grounded: true / false           │
                                                                        │ • confidence_rating: 0.0 – 1.0        │
                                                                        └───────────────────┬───────────────────┘
                                                                                            ▼
                                                                        ┌───────────────────────────────────────┐
                                                                        │ Log INSERT INTO rag_query_log         │
                                                                        └───────────────────────────────────────┘
```

### 5.2 Deterministic Grounding & Verification Guarantees
1. **Summary-Level Indexing:** Raw posts are never embedded directly into the vector store. Instead, analytical agents (B, C, D, E) generate dense, structured 2–4 sentence summaries indexed with strict temporal metadata (`window_start` to `window_end` in UTC).
2. **Tier 0 Hard Mathematical Cutoff (`< 0.65`):** Queries matching no summary chunks with cosine distance $< 0.65$ trigger an immediate short-circuit. The LLM is **never called**, providing an unbreachable mathematical guarantee against hallucinating on queries outside the monitored domain.
3. **Tier 1 Temporal Relevance Filtering:** Candidate documents passing Tier 0 are filtered for temporal consistency against query timeframe envelopes.
4. **Tier 2 Single-Pass Structured Contract:** The prompt enforces a Pydantic structured output contract (`GroundedAnalystResponse`): `relevance_grade`, `answer`, `cited_document_ids`, `is_grounded`, and `confidence_rating`. Single pass avoids multi-turn loops that would freeze local Ollama inference on a laptop.
5. **Tier 3 Audit Trail Logging:** Non-bypassable logging to `rag_query_log` occurs prior to returning the HTTP payload, recording query text, retrieved chunk IDs, generated response, confidence rating, and grounding status.

---

## 6. Data Governance, Regulatory Alignment & Post-Viva PII Scrub

### 6.1 Gated Research Authorisation & OSINT Boundary
- **Public OSINT Boundary:** Ingestion operates strictly on publicly accessible Telegram broadcast channels via Pyrofork MTProto. No private groups, private chats, or encrypted direct messages are ever accessed.
- **Supervisor Gating:** Operational channel monitoring is formally signed off with the project faculty supervisor as research into public social communication spaces.

### 6.2 Regulatory Alignment (CERT-In Directions & DPDP Act 2023)
While the framework is an academic research prototype exempt from commercial intermediary reporting obligations, the system aligns with core principles:
1. **CERT-In Timestamp Synchronization:** All ingested events and analytical timelines are strictly anchored to UTC `TIMESTAMPTZ` (`posted_at`), ensuring non-skewed chronological ordering.
2. **CERT-In Analyst Auditability:** Every analyst query against the RAG interface is logged with query text, timestamp, and retrieved document IDs into `rag_query_log`.
3. **DPDP Act 2023 Compliance via $k$-Anonymity ($k \ge 50$):** In Component C, individual-level profiling is prevented. Demographic clusters with fewer than 50 accounts are suppressed (`below_threshold: true`).
4. **Advisory Anomaly Detection:** Component E outputs anomaly scores as probabilistic screening signals ($0.0$ to $1.0$), never definitive verdicts.
5. **Protective Pseudonymization:** Monitored authors in graph visualizations are masked (e.g., `Actor-[Masked]-XXX`).

### 6.3 Post-Viva PII Disposal Routine
To satisfy ethical data retention without building complex custom database infrastructure, personal text and user metadata are wiped from the development database post-viva:

```sql
-- Committed End-of-Semester PII Scrub Routine (scripts/post_viva_scrub.sql)
BEGIN;

-- 1. Wipe raw message content and media attachments
UPDATE raw_posts 
SET content_text = NULL,
    media_urls = NULL;

-- 2. Wipe author personal identifiers
UPDATE raw_authors 
SET display_name = NULL,
    bio_text = NULL;

COMMIT;
```

---

## 7. Storage Performance & Indexing Scheme

```sql
-- 1. Component B row-level processing queue (high-frequency worker poll)
CREATE INDEX idx_raw_posts_pending ON raw_posts (id) WHERE processing_status = 'pending';

-- 2. Temporal range queries for sliding windows (Components C, D, E)
CREATE INDEX idx_raw_posts_posted_at ON raw_posts (posted_at DESC);

-- 3. Vector cosine distance index via HNSW
CREATE INDEX idx_rag_documents_hnsw ON rag_documents USING hnsw (embedding vector_cosine_ops);
```

---

*Document version: 4.8 (Architecture Specification & Engineering Reference) | Aligned with Project Brief v4.8 & Cursor Brief v4.8 | October 2026*
