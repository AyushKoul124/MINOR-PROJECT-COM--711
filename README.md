# 📡 AI-Driven Social Media Audience Intelligence Framework

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.11x-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-Hugging%20Face-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org/)

> **COM-711 — 7th-semester CSE minor project · Team of 4 · September–December 2026**

An offline-first audience-analysis prototype for public Telegram posts. Five components save the posts, read each one, sketch the group, find themes, and draw the interaction graph. A seven-page dashboard shows the posts, the readings, and an Ask page that answers only from the system's own summaries.

The National Technical Research Organisation published the problem statement. This repository is the student testbed for the viva. It is a research prototype. Phase 5 scored two coordination signals on a labelled tweet file: at the 0.70 cutoff, precision is 1.00, recall is 0.04, and F1 is 0.0769. That number is an offline check. It is not a dashboard accuracy.

The demonstration that has to work in the exam room is the offline seed and the local dashboard. Live Telegram and an online language model are optional.

**Reference machine.** NVIDIA GeForce GTX 1650 Ti (4 GB), 16 GB RAM, Windows 11. The same code runs on CPU. The labels stay the same. The run takes longer.

---

## 📋 Table of Contents

1. [Architecture](#-architecture)
2. [Data](#-data)
3. [Installation](#-installation)
4. [Quick Start](#-quick-start)
5. [Components](#-components)
6. [Dashboard](#-dashboard)
7. [Operating figures](#-operating-figures)
8. [Project Structure](#-project-structure)
9. [Team](#-team)
10. [Documents](#-documents)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│        Audience Intelligence Framework  ·  academic prototype    │
└──────────┬──────────────┬──────────────┬──────────────┬──────────┘
           │              │              │              │
   ┌───────▼────┐  ┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐
   │ A          │  │ B           │ │ C         │ │ D          │
   │ Ingestion  │  │ Sentiment   │ │ Audience  │ │ Trends     │
   │            │  │             │ │           │ │            │
   │ • seed     │  │ • valence   │ │ • k ≥ 50  │ │ • BERTopic │
   │ • export   │  │ • emotion   │ │ • IST day │ │ • velocity │
   │ • live     │  │ • stance    │ │ • sketch  │ │ • 500 cap  │
   └────────────┘  └─────────────┘ └───────────┘ └────────────┘
           │              │              │              │
           └──────────────┴──────┬───────┴──────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │ E  Network              │
                    │ forwards · replies ·    │
                    │ mentions · 3-signal avg │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────▼──────────────────┐
              │  React dashboard   :5173            │
              │  FastAPI           :8000            │
              │  PostgreSQL + pgvector   Redis 7    │
              └─────────────────────────────────────┘
```

Docker runs only PostgreSQL 16 (with pgvector) and Redis 7. The API, the models, and the website run on the host. The browser talks to FastAPI. FastAPI talks to the database.

| Letter | Package | Writes |
| --- | --- | --- |
| A | `ingestion_a/` | `monitored_channels`, `raw_posts`, `raw_authors`, `ingestion_runs` |
| B | `sentiment_b/` | `sentiment_results_b` |
| C | `demographic_c/` | `demographic_aggregates_c` |
| D | `trend_d/` | `trend_topics_d` |
| E | `network_e/` | `network_nodes_e`, `network_edges_e` |
| — | `orchestrator/` | Runs B, then refreshes C, D, and E |
| — | `rag/` | `rag_documents`, `rag_query_log` |

`posted_at` is the time on the Telegram message. Every window, speed, and synchrony check uses that clock. `ingested_at` only records when the row was stored.

**Run analysis** takes at most 50 waiting posts that contain words, scores them one model at a time, then recomputes the audience, the themes, and the graph for the window. On the reference GPU that capped path is specified at 15–25 seconds.

---

## 📦 Data

Public Telegram channels and groups. Private one-to-one chats are outside the collection design. X/Twitter, Reddit, YouTube, Instagram, and Facebook are not collected.

| Property | Detail |
| --- | --- |
| **Scale** | About 30 channels, hundreds to a few thousand posts |
| **Review batch** | At most 50 posts with text |
| **Window** | Usually the last 48 hours, measured on `posted_at` |
| **Photos** | `Telegram Desktop/<channel>/photos/<message id>.jpg` |
| **Reactions** | Emoji → count, stored on the post |
| **Comments** | Replies in the same chat, plus discussion-thread replies |
| **Offline seed** | `python -m ingestion_a.backfill --offline` |

| Live command | What it pulls |
| --- | --- |
| `python -m ingestion_a.download_latest` | Project-related chats, latest 80 messages |
| `python -m ingestion_a.download_latest --middle-east` | Middle East titles first, no 80-message cap. India's North East is a different subject. |
| `python -m ingestion_a.download_latest --indian-defence` | Indian defence titles first, latest 80. Gore, academies, and job boards stay out. |
| `python -m ingestion_a.download_latest --comments` | Discussion replies on the newest 48 stored posts, at most 25 each |

A repeated message is recognised by platform and message id. A later import may refresh the photo path, the reaction counts, and the view count. Analysed text and `posted_at` stay as they are. One live client may hold the session file.

Discussion comments are stored with `_comment_` in the id and `reply_to_id` set to the parent message, so they appear under that post. A channel with no linked discussion contributes no thread. Phone numbers are never stored.

---

## ⚙️ Installation

```bash
git clone https://github.com/AyushKoul124/MINOR-PROJECT-COM--711.git
cd MINOR-PROJECT-COM--711

Copy-Item .env.example .env          # Windows PowerShell
docker compose up -d

python -m venv .venv
.\.venv\Scripts\Activate.ps1         # Windows
pip install -r requirements.txt
alembic upgrade head
```

The first migration enables `CREATE EXTENSION IF NOT EXISTS vector`. Database defaults match `docker-compose.yml`: database `socmint`, user `postgres`, port 5432.

`.env`, `frontend/.env`, `*.session`, and `Telegram Desktop/` stay out of git.

---

## 🚀 Quick Start

```bash
# Exam path. No Telegram account required.
python -m ingestion_a.backfill --offline
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. API docs are at **http://127.0.0.1:8000/docs**.

`scripts/start_system.ps1` checks PostgreSQL, aligns the seed into the active 48-hour window, and starts the API and the website.

Optional, when a network and a Telegram session are available:

```bash
python -m ingestion_a.download_latest --middle-east
python -m ingestion_a.download_latest --indian-defence
python -m ingestion_a.download_latest --comments
```

Offline answers, when Ollama is installed:

```bash
ollama serve
ollama pull llama3.2:3b
```

Set `LLM_PROVIDER=ollama`. If the model is down, Ask still returns the retrieved extract.

After the exam:

```bash
psql -U postgres -d socmint -f scripts/post_viva_scrub.sql
```

---

## 🔬 Components

### 1. 📥 Ingestion (`ingestion_a/`)

Saves a public post. It does not label sentiment, topic, or coordination.

- **Doors:** offline seed, Telegram Desktop HTML/JSON export, optional live reader (Pyrofork)
- **Photos:** one JPEG per message, under `Telegram Desktop/<channel>/photos/`
- **Paging:** 80 messages per page, continued from the last message id when the cap is lifted
- **Flood wait:** flush the rows already held, sleep for the time Telegram returns, resume the same chat
- **Subject filter:** titles are folded to plain letters. Blocked words match as whole words. Force-include is an exact folded title, so `Rootsec` is kept and `Rootsec [Cracked Softwares]` is excluded

```bash
python -m ingestion_a.backfill --offline
python -m ingestion_a.import_exported --import-all-dirs "Telegram Desktop" --max-posts 80
```

---

### 2. 💬 Sentiment, emotion, and stance (`sentiment_b/`)

One row in `sentiment_results_b` per post that has words. The text readings and the reaction bar stay separate.

| Reading | Method | Output |
| --- | --- | --- |
| Sentiment | `cardiffnlp/twitter-xlm-roberta-base-sentiment` (~1.1 GB) | positive, neutral, negative |
| Emotion | `SamLowe/roberta-base-go_emotions` (~500 MB) | Ekman six + neutral |
| Stance | `valhalla/distilbart-mnli-12-3` (~260 MB) | supportive, against, neutral, unclear |
| Sarcasm | Text and emoji rules. No neural model. | A flag. Confidence drops. The valence label stays. |
| Reaction bar | `(positive − negative) / (positive + negative)` | Separate score. Cutoff 0.15. Unmapped emoji stay out of the ratio. |

Stance below 0.60 is not forced onto a side. The models load one at a time, then the card is freed. `facebook/bart-large-mnli` (~1.6 GB) is for the written comparison only.

```python
from sentiment_b.reactions import score_reactions

reading = score_reactions(post.reaction_counts)
# reading.valence, reading.score, reading.top
```

Newest `posted_at` is read first. A `pending` post stays off the Sentiment page until this step finishes. Overview shows that post before then.

---

### 3. 👥 Audience (`demographic_c/`)

A keyword sketch of the group in the window: coarse age bands, region hints, language, interests, and the hour the posts arrived.

- **Floor:** k-anonymity, k = 50. A smaller group is stored with `below_threshold`. The research line stays at 50. A demo card may use 15 and must be described as below the line.
- **Empty card:** `account_count` under 1 draws no age, place, language, or interest bars.
- **Clock:** `posted_at` shifted to IST (UTC+5:30). Morning 06–12, afternoon 12–18, evening 18–23, night 23–06. All 24 hours are drawn.
- **Snapshots:** each run inserts a new row. The page keeps the newest snapshot of each label.

Anyone who never writes is absent. The collector has no subscriber list.

---

### 4. 📈 Trends (`trend_d/`)

Clusters posts in the window and ranks the clusters by speed.

- **Embedder:** `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions. Ask uses the same model.
- **Cluster:** BERTopic + HDBSCAN, `min_topic_size = 3`, input capped at 500 documents
- **Velocity:** posts in the theme ÷ hours in the whole window
- **Acceleration:** second half of the window compared with the first. A positive change is the rising mark.

The theme name is an extracted term list. D clusters raw text and does not wait for Component B.

---

### 5. 🕸️ Network (`network_e/`)

A directed graph of forwards, replies, and mentions. Louvain runs on a real undirected copy (`import community` from `python-louvain`). The drawing keeps the directed edges.

| On the page | Meaning |
| --- | --- |
| Node | A channel or a public author |
| Line | A forward, a reply, or a mention |
| Size | Betweenness |
| Colour | Louvain community |
| Mark | Behaviour score ≥ 0.70 |

The API returns at most 500 nodes, the highest by betweenness. Edges are those whose both ends are in that set.

```text
anomaly_score = (posting_synchrony + age_volume + duplicate_content) / 3
```

Synchrony uses a 120-second window. Near-duplicates use TF-IDF. A missing account-creation date weakens the age signal. The score runs from 0.0 to 1.0 and is an advisory screen. Zero flagged accounts is a valid result.

---

### 6. ❓ Ask (`rag/`)

Searches the short summaries B, C, D, and E have already written.

1. Embed the question with MiniLM.
2. Retrieve nearest summaries from pgvector by cosine distance.
3. Distance greater than 0.65 stops the question.
4. Otherwise one language model writes a short answer from those passages.
5. The question, the passages, and the answer go to `rag_query_log`.

| `LLM_PROVIDER` | Writer |
| --- | --- |
| `ollama` | Local `llama3.2:3b`, about 2 GB, 4-bit. Air-gapped path. |
| `groq` | Groq, when `GROQ_API_KEY` is set |
| `xai` | xAI, when `XAI_API_KEY` starts with `xai-` |
| Anything else, or an unreachable model | The retrieved extract. No network call. |

---

## 🖥️ Dashboard

React 18 and Vite 6. Styling is the project's own CSS: a light editorial page, white cards, blue marks. Tailwind, Recharts, and a force-graph library are named in early notes and are not in `package.json`. Vite proxies `/api` to `127.0.0.1:8000`.

| Page | Route | What it shows |
| --- | --- | --- |
| Overview | `GET /api/overview`, `GET /api/overview/posts` | Saved and waiting counts, then the posts |
| Sources | `GET /api/datasources` | Where the rows came from |
| Sentiment | `GET /api/sentiment/timeline` | Text-model bars, and a separate reaction row |
| Audience | `GET /api/demographics` | Group sketch and the IST hour chart |
| Trends | `GET /api/trends` | Terms, velocity, acceleration |
| Network | `GET /api/network/graph` | The directed graph |
| Ask | `POST /api/rag/query` | The answer and the passages under it |

Overview splits picture posts and text posts. Opening a card shows the channel, the message time, every saved photo, the full caption, the reaction emoji with counts, and the comments. The card itself shows the chips, the comment count, and the first comment.

`GET /api/media` serves one JPEG, PNG, or WebP inside `Telegram Desktop/`. That route is public, because an image tag sends no Basic Auth header. `GET /api/health` is public. Every other `/api` route expects HTTP Basic credentials when `API_BASIC_AUTH_PASSWORD` is set.

There are seven pages. Report export was removed from the product. The PDFs in `docs/review/` are team handouts.

**A two-minute pass**

1. Overview — open one picture post and one text post. Reactions are emoji counts. Comments are replies.
2. Sources — collection writes rows and stops there.
3. Sentiment — bars are the wording. The reaction row is separate. Sarcasm does not flip the label.
4. Audience — under 50 accounts, the card is below the privacy line. The hours are counted from `posted_at`.
5. Trends — a rising theme is faster in the second half of the window.
6. Network — a mark at 0.70 is the advisory screen.
7. Ask — one prepared question, and the passages under the answer.

---

## 📊 Operating figures

These are the locked limits of the prototype. They are design choices, not measured accuracy.

| Figure | Value | Where it binds |
| --- | --- | --- |
| Review batch | ≤ 50 posts | Run analysis |
| Specified time on the GTX 1650 Ti | 15–25 s | That capped batch only |
| Stance line | 0.60 | Below it, the post is not placed on a side |
| Reaction cutoff | 0.15 | Separate from the text label |
| Ask distance cutoff | 0.65 | Farther than this, the question stops |
| Behaviour flag | 0.70 | Unweighted mean of three signals |
| Audience floor | k = 50 | Demo cards may use 15 and are marked below the line |
| Theme input | 500 documents | `min_topic_size = 3` |
| Graph cap | 500 nodes | Highest betweenness, induced edges |
| VRAM discipline | one transformer at a time | 4 GB card |

Phase 5 compared the coordination screen with `all_tweets_hashed.csv`, the Kaggle information-operations table (`info_op` 1 = coordinated, 0 = organic). The file has 22,873,094 tweet rows and 4,427 organic plus 4,167 coordinated accounts. The score uses a fixed sample: seed 42, 400 accounts from each class, at most 25 tweets from each account. The reported score is the mean of posting synchrony and duplicate content. `age_volume_signal` is excluded because the file has no account-creation date.

| Check at 0.70 | Precision | Recall | F1 | Flagged |
| --- | --- | --- | --- | --- |
| Mean of the two signals | 1.00 | 0.04 | 0.0769 | 16 coordinated, 0 organic |
| Synchrony alone | 1.00 | 0.0475 | 0.0907 | 19 coordinated, 0 organic |
| Duplicate content alone | 0.8019 | 0.2125 | 0.3360 | 85 coordinated, 21 organic |

A flag at 0.70 was right whenever it fired, and it fired for 16 of the 400 coordinated accounts in the sample. Lower cutoffs on the same sample trade that precision away for more of the coordinated class. At 0.50, precision is 0.9388, recall is 0.23, and F1 is 0.3695. The full curve is in `benchmarks/cib_ioa/results.json`. The tweets are from a Twitter / Russian-operation collection. The live system reads Telegram. These figures are indicative.

Also still open: a full pass of Component B over every pending row, the complete history of every Middle East channel, discussion comments beyond the newest 48 posts, and the 15–25 second figure on CPU or on a batch larger than 50.

---

## 📁 Project Structure

```
MINOR-PROJECT-COM--711/
├── README.md
├── docker-compose.yml              # PostgreSQL 16 + pgvector, Redis 7
├── requirements.txt
├── alembic.ini
│
├── ingestion_a/                    # A  seed, export import, live reader
├── sentiment_b/                    # B  valence, emotion, stance, reactions
├── demographic_c/                  # C  audience sketch, IST hours
├── trend_d/                        # D  BERTopic, velocity
├── network_e/                      # E  graph, Louvain, three-signal score
├── benchmarks/cib_ioa/             # Offline precision, recall, and F1
├── orchestrator/                   # Run analysis, optional Celery beat
├── rag/                            # MiniLM search, 0.65 cutoff, answer writer
│
├── api/                            # FastAPI routes, Basic Auth, media files
├── frontend/                       # React 18 dashboard, seven pages
├── storage/                        # SQLAlchemy models, Alembic migrations
├── config/                         # Channel list
├── scripts/                        # Windows launchers, post-viva purge
└── docs/review/                    # Second-review briefs (PDF)
```

---

## 👨‍💻 Team

Four members. Ownership follows the implementation plan. Personal names are on the course roll, not in this file.

| Member | Owns | Packages |
| --- | --- | --- |
| **P1** | Collection, storage, infrastructure | `ingestion_a/`, `storage/`, Docker, offline seed |
| **P2** | Sentiment, stance, themes | `sentiment_b/`, `trend_d/` |
| **P3** | Network, orchestration | `network_e/`, `orchestrator/` |
| **P4** | Audience, Ask, dashboard | `demographic_c/`, `rag/`, `frontend/` |

Institution: Model Institute of Engineering and Technology (Autonomous).

Every member is expected to defend every part at the viva.

---

## 📄 Documents

| Document | Path |
| --- | --- |
| The whole project, in plain words | [docs/review/Whole_Project_Plain_Words.pdf](docs/review/Whole_Project_Plain_Words.pdf) |
| Stack, data, and build notes | [docs/review/Stack_Data_and_Challenges.pdf](docs/review/Stack_Data_and_Challenges.pdf) |
| Component A | [docs/review/Component_A_Ingestion.pdf](docs/review/Component_A_Ingestion.pdf) |
| Component B | [docs/review/Component_B_Sentiment.pdf](docs/review/Component_B_Sentiment.pdf) |
| Component C | [docs/review/Component_C_Audience.pdf](docs/review/Component_C_Audience.pdf) |
| Component D | [docs/review/Component_D_Trends.pdf](docs/review/Component_D_Trends.pdf) |
| Component E | [docs/review/Component_E_Network.pdf](docs/review/Component_E_Network.pdf) |
| Locked brief | [PROJECT_BRIEF.md](PROJECT_BRIEF.md) |
| Architecture note | [ARCHITECTURE.md](ARCHITECTURE.md) |

```bash
.\.venv\Scripts\python.exe docs\review\build_review_pdfs.py
```

Where this README and an older note disagree on a route name or a frontend library, the running code is the one to demonstrate. The live routes are `/api/sentiment`, `/api/trends`, `/api/demographics`, `/api/network`, `/api/rag`, and `/api/datasources`.

---

Academic prototype · Python · FastAPI · React · PostgreSQL · public Telegram posts
