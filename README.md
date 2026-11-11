# AI-Driven Social Media Audience Intelligence Framework

**Academic proof of concept · 7th-semester CSE minor project · Team of 4 · September–December 2026**

This repository is a working research prototype that collects public Telegram posts and turns them into seven dashboard views. It reads each post for wording, emotion, and stance, then summarises a time window as an audience sketch, a set of themes, and an interaction graph. A natural-language question is answered only from the short summaries those steps write, and only when a summary is close enough to cite.

The system is a student testbed. The public problem statement is the only connection to its origin. This software is not an operational intelligence system, is not deployed by any agency, and does not claim an accuracy percentage. Every teammate is expected to be able to explain every part at the viva.

The product that must work in the exam room is the offline seed plus the local dashboard. Live Telegram and an online language model are optional. Campus networks, Telegram rate limits, and a missing API key must not be able to cancel the demonstration.

**Reference machine.** NVIDIA GeForce GTX 1650 Ti, 4 GB graphics memory, 16 GB RAM, Windows 11. A machine without a usable GPU runs the same code on the CPU. The labels do not change. The run takes longer.

---

## 1. What the system is for

The prototype answers five kinds of question about a recent window of public posts:

- How does the wording lean, and how does that differ from the emoji reactions under the posts?
- Which clusters of similar posts are arriving faster in the later half of the window?
- What can be said about the group that spoke, without assigning an age or a place to one named person?
- Which accounts sit on the paths between others, and which behaviour scores are high enough to flag for a closer look?
- What do the system’s own summaries say about a question, and when should it refuse to answer?

Those answers appear as charts and tables, and again through the Ask page. Ask does not browse the raw archive and invent a paragraph. It searches stored summaries. If nothing is close, it stops.

## 2. Scope

| In this prototype | Outside this prototype |
| --- | --- |
| Public Telegram channels and groups | Private one-to-one chats as a collection design |
| An offline seed that needs no network | A claim that the live account is required for the exam |
| Five analysis agents and one coordinator | A multi-agent framework such as LangGraph or CrewAI |
| Seven dashboard pages over HTTP | A PDF button inside the dashboard, or a live socket |
| Aggregate audience sketches | A dossier on one person |
| An advisory behaviour screen | A verdict that an account is a bot or that a campaign is real |
| Published models, used as released | A model trained by the team, or a quoted accuracy percentage |

X/Twitter is not collected live. Reddit, YouTube, Instagram, and Facebook are not implemented. A later report may discuss an offline coordination file for two of the three network signals. That benchmark has not been run, so this README does not quote precision or recall.

The intended operating scale is about 30 public channels and hundreds to a few thousand historical posts. The review button is specified for a batch of at most 50 posts, not for the whole archive.

## 3. Architecture

The browser never opens the database. It calls a FastAPI process. That process reads and writes PostgreSQL. Redis is present for background jobs. Docker runs only PostgreSQL 16 with the pgvector extension, and Redis 7. The API, the models, and the website run on the host.

```text
React dashboard (port 5173)
        |
        |  HTTP, Basic Auth on /api except /api/health
        v
FastAPI (port 8000)
        |
        +--> PostgreSQL 16 + pgvector     raw posts, analysis rows, Ask log
        +--> Redis 7                      broker for the optional Celery cycle
        |
        +--> Component A   save a post
        +--> Component B   read one post
        +--> Components C, D, E   recompute a time window
        +--> Ask           search summaries, then write one answer
```

Five packages are the analytical identity of the project. The letters are stable: a table, a module, and a review brief can be traced to the same letter.

| Letter | Package | Kind of work | What it writes |
| --- | --- | --- | --- |
| A | `ingestion_a/` | Save public posts | `monitored_channels`, `raw_posts`, `raw_authors`, `ingestion_runs` |
| B | `sentiment_b/` | Read one post | `sentiment_results_b` |
| C | `demographic_c/` | Sketch a group | `demographic_aggregates_c` |
| D | `trend_d/` | Find themes and their speed | `trend_topics_d` |
| E | `network_e/` | Draw the graph and screen behaviour | `network_nodes_e`, `network_edges_e` |
| — | `orchestrator/` | Run B, then refresh C, D, and E | — |
| — | `rag/` | Search summaries and answer | `rag_documents`, `rag_query_log` |
| — | `api/`, `frontend/` | Serve the seven pages | — |

### Two different clocks, and two different triggers

`posted_at` is the time Telegram put on the message. `ingested_at` is the time this program stored the row. Every window, every speed calculation, and every synchrony check uses `posted_at`. Using the download time would measure our delay, not the conversation.

Component B is the only row runner. A new post is `pending`. After B finishes, the code marks it `processed`. Components C, D, and E do not look at that flag. Each of them reads every post whose `posted_at` falls inside the window, usually the last 48 hours, and writes a fresh snapshot. At this project’s size a full recompute is simpler than an incremental topic model or an incremental graph, and it is the locked design.

The background design is a Celery Beat cycle: collection staggered across the channels, B on a short cycle, C and D less often, E less often still. The ingestion worker must run at `--concurrency=1`, because the Telegram session file is a single SQLite file. The review does not have to wait for that cycle. **Run analysis** calls the same coordinator immediately.

### What “Run analysis” actually does

1. Take waiting posts that contain words. Stop at 50 for the review button.
2. Load the sentiment model, score the batch, and free the graphics card.
3. Load the emotion model, score the batch, and free the card.
4. Load the stance model, score the batch, and free the card.
5. Apply the sarcasm rule and the reaction-bar score. Neither needs the graphics card.
6. Mark those posts `processed`.
7. Recompute the audience, the themes, and the graph for the window. Theme input is capped at 500 documents.
8. Embed the short summaries so Ask can search them.

On the reference GPU, that capped path is specified to finish in 15 to 25 seconds. That sentence is not a promise for a CPU laptop, and it is not a promise for thousands of posts. Empty captions are skipped: a photograph with no words cannot be given a text label.

## 4. Component A — collection

Collection stores a public post once. It does not decide whether the wording is positive, topical, or coordinated.

Three doors write the same tables.

| Door | Command | When it is used |
| --- | --- | --- |
| Offline seed | `python -m ingestion_a.backfill --offline` | The review, and any room without a stable network. Prepared posts are given recent times so the 48-hour pages are not empty. |
| Desktop export | `python -m ingestion_a.import_exported` | A Telegram Desktop export, HTML (`messages.html`) or JSON (`result.json`). |
| Live reader | `python -m ingestion_a.download_latest` | Optional. Public channels and groups whose titles match the project subjects. |

The live reader keeps the latest 80 messages and any photos, which are saved under `Telegram Desktop/<channel>/photos/`. History longer than one page is read in pages of 80, continuing from the last message id, so a full-history run is not cut off after the first page. A repeated message is recognised by platform and message id. The second import may update the photo path, the reaction counts, and the view count. It does not wipe text that has already been analysed, and it does not move `posted_at`.

| Command | What it pulls |
| --- | --- |
| `python -m ingestion_a.download_latest` | Project-related public chats, latest 80 messages each |
| `python -m ingestion_a.download_latest --middle-east` | Middle East titles first. Mediterranean Man, Middle East Spectator, and MiddleEast GC lead. No 80-message cap. India’s North East is not treated as the Middle East. |
| `python -m ingestion_a.download_latest --indian-defence` | Indian defence titles first (army, navy, air force, named defence channels). Still capped at 80. Gore channels, academies, and job boards stay out. |
| `python -m ingestion_a.download_latest --comments` | Discussion replies for the newest posts already in the database, up to 25 replies on each of the newest 48 posts |

Books, films, job posts, and cracked software are left out of every mode. Decorative Unicode in a title is folded to plain letters before the subject check, otherwise a real channel looks like a random string. The force-include list is an exact title after that fold, so “Rootsec” is kept and “Rootsec [Cracked Softwares]” is not.

If Telegram returns a flood wait, the reader sleeps for the time Telegram demands, flushes the rows already collected, and then continues the same chat.

A stored post holds the text, the message time, the view count, the reaction counts, a photo path when a picture was saved, the id of the message it replies to, and the processing status. Comments from a channel’s linked discussion are stored as their own rows. Their id contains `_comment_`, and `reply_to_id` points at the channel post, so the overview can show them under that post instead of as a second card. A public display name is stored when a person actually wrote a comment. Phone numbers are not stored. Subscriber lists are not available from the interface this project uses.

Some channels have no linked discussion. Telegram then refuses the comment request, and that post stays without a comment thread. Replies that were already inside the same chat are still shown.

## 5. Component B — one post

B writes one row in `sentiment_results_b` for each post it can read. The four text readings and the reaction bar stay separate. A crowd of likes does not rewrite the text label.

| Reading | Method | Output |
| --- | --- | --- |
| Sentiment | `cardiffnlp/twitter-xlm-roberta-base-sentiment` | Positive, neutral, or negative. About 1.1 GB. |
| Emotion | `SamLowe/roberta-base-go_emotions`, mapped to Ekman’s six emotions plus neutral | Joy, anger, sadness, fear, disgust, surprise, or neutral. About 500 MB. |
| Stance | `valhalla/distilbart-mnli-12-3` against the channel topic | Supportive, against, neutral, or unclear. About 260 MB. |
| Sarcasm | Rules on the text and the emoji. No neural model. | A flag. Confidence drops. The sentiment label is not flipped. |
| Reaction bar | Positive emoji against negative emoji, divided by their sum | A separate score. The cutoff is 0.15. Unmapped emoji, including “?”, do not move it. |

Stance uses a hard threshold of 0.60. If the best score is below that line, the post is not forced onto a side. The larger BART checkpoint, about 1.6 GB, is a comparison for the written report only. It is not loaded in the demo.

The models are Hugging Face checkpoints used off the shelf. The team did not train them. They run one after another because the reference card cannot hold them together. If CUDA is unavailable, the same order runs on the CPU.

Newest `posted_at` values are read first, so a freshly saved post is not stuck behind an older backlog. The Sentiment page shows analysed posts inside the 48-hour window, including the first saved photo when the post has one. A post that is still `pending` does not appear there. That is the difference between “saved” and “read”. The Overview page does not wait for this step: a saved post is visible there with its picture, reactions, and comments before B has run.

## 6. Component C — the group, not the person

C summarises who appears to be speaking in the window: coarse age bands, region hints, language, interests, and the hours posts arrive in India Standard Time. The inputs are public. A broadcast channel contributes its name, its topic tags, and the hours it posts. A discussion contributes the public display name and bio of people who actually wrote. Anyone who never speaks is invisible, because Telegram does not provide the subscriber list. The result is a keyword sketch, not a census.

The privacy rule is k-anonymity with k at least 50, in line with the data-minimisation idea of India’s DPDP Act 2023. A group smaller than 50 accounts is stored with `below_threshold` set. The research line stays 50. A demo run may use 15 so a small seed still produces a card. A card under 50 must be described as below the line, not as a finding about a population. A card with nobody speaking under a public name does not draw age, place, language, or interest bars. The page keeps the newest snapshot of each group label, so a repeated run does not stack identical cards.

The hour chart is counted from `posted_at`, converted to India Standard Time (UTC+5:30). Morning is 06:00–12:00, afternoon 12:00–18:00, evening 18:00–23:00, and night 23:00–06:00. The page draws all 24 hours and names the busiest hour. Those ratios are not a fixed template.

Each run inserts a new snapshot. It does not silently invent accounts to reach 50.

## 7. Component D — themes and speed

D groups posts in the window into themes and ranks those themes by how fast they are being posted.

1. Take posts in the window that have text. The clock is `posted_at`.
2. Embed each post with `paraphrase-multilingual-MiniLM-L12-v2`. The same model embeds Ask queries. The vector length is 384.
3. Cluster with BERTopic and HDBSCAN. The minimum topic size is 3, so a small student corpus can still form a theme.
4. Cap the run at 500 documents so memory stays bounded.
5. Name the theme from its distinctive words. Those words are extracted terms, not a headline written by a person.

The window is then split in half. Velocity is posts in the theme divided by hours in the whole window. Acceleration compares the second half with the first. A positive change is the “rising” mark. A negative change means the theme is cooling. Neither number is a prediction of tomorrow.

D does not decide who is coordinated. That question belongs to Component E. D also does not require B to have finished: it clusters raw text.

## 8. Component E — the graph and the screen

E builds a directed graph of public interactions: forwards, replies, and mentions. Community detection needs an undirected graph, so the code makes a real undirected copy and runs Louvain from the `python-louvain` package (`import community`). The drawing keeps the directed edges.

| On the page | Meaning |
| --- | --- |
| Node | A channel or a public author |
| Line | A forward, a reply, or a mention |
| Size | Betweenness: how often the account sits on paths between others |
| Colour | Louvain community on the undirected copy |
| Mark | The behaviour score is at least 0.70 |

The API returns at most 500 nodes, the ones with the highest betweenness. Edges are only those whose both ends are in that set.

The score is an unweighted average of three signals. There are no learned weights.

| Signal | Question |
| --- | --- |
| Posting synchrony | Do this account’s posts land within two minutes of other posts unusually often? |
| Age and volume | Is a young account posting a lot? A missing creation date weakens this signal. |
| Near-duplicate text | Is the wording unusually similar to other text in the window? Similarity here is TF-IDF, not the neural embedder. |

`anomaly_score = (s1 + s2 + s3) / 3`. A flag is raised at 0.70. Both choices are locked so they can be written on a whiteboard. The flag is an advisory screen. It is not attribution, and it is not a bot label. Zero flagged accounts is a result, not a broken page.

## 9. Ask

Ask is not a sixth analysis. It searches the short summaries B, C, D, and E have already written.

1. Embed the question with the same MiniLM model.
2. Retrieve the nearest summaries from pgvector by cosine distance.
3. If the nearest distance is greater than 0.65, stop. A fluent invention is worse than no answer.
4. Otherwise one language model writes a short answer from those passages only.
5. Write the question, the passages, and the answer to `rag_query_log`.

The writer depends on `LLM_PROVIDER` in `.env`.

| Setting | Writer |
| --- | --- |
| `ollama` | Local `llama3.2:3b`, about 2 GB, 4-bit. This is the air-gapped path. |
| `groq` | Groq, only when `GROQ_API_KEY` is set |
| `xai` | xAI, only when `XAI_API_KEY` is set and begins with the `xai-` prefix |
| Anything else, or no reachable model | A short extract of the retrieved summaries. No network call. |

Search always happens in Postgres first. The language model never sees the raw archive. Keys stay in `.env`. They are not stored in this repository.

## 10. Data stored in PostgreSQL

The first migration enables `CREATE EXTENSION IF NOT EXISTS vector`. Later migrations add the emotion columns and the reaction score.

| Table | Holds |
| --- | --- |
| `monitored_channels` | Channel name, topic tags, last check |
| `raw_posts` | Text, photo path, views, reactions, reply target, both timestamps, processing status. Discussion comments use an id containing `_comment_`. |
| `raw_authors` | Public display name and bio snapshot, when a discussion author is visible |
| `ingestion_runs` | One record per collection run |
| `sentiment_results_b` | One reading per post |
| `demographic_aggregates_c` | One audience snapshot per run and group label |
| `trend_topics_d` | Themes, velocity, and acceleration for one window |
| `network_nodes_e`, `network_edges_e` | The graph for one window |
| `rag_documents` | Embedded summaries, 384 dimensions |
| `rag_query_log` | Every question and the passages used to answer it |

After the exam, `scripts/post_viva_scrub.sql` sets message text, display names, and bios to null. That is the approved way to clear personal text. The project does not keep a second compliance ledger.

## 11. The dashboard

The website is React 18, built with Vite 6. Styling is the project’s own CSS: a light editorial page, white cards, and blue marks. Tailwind, Recharts, and a force-graph library appear in early notes and were not added. The development server proxies `/api` to `127.0.0.1:8000`.

| Page | Route in the API | What a reviewer should hear |
| --- | --- | --- |
| Overview | `GET /api/overview` and `GET /api/overview/posts` | Counts of saved posts and posts still waiting, then the posts themselves |
| Sources | `GET /api/datasources` | Collection writes rows. It does not analyse them. |
| Sentiment | `GET /api/sentiment/timeline` | The bars are the text model. The reaction row is the audience tapping emoji. |
| Audience | `GET /api/demographics` | A group sketch, and an hour chart counted from message time in IST. Say the number out loud if it is under 50. |
| Trends | `GET /api/trends` | Extracted terms and a speed, on the message clock |
| Network | `GET /api/network/graph` | A mark at 0.70 is a screen, not an accusation |
| Ask | `POST /api/rag/query` | Point at the passages under the answer |

Overview does not wait for Component B. `GET /api/overview/posts` returns the newest saved posts whether or not they have been read. Each card is either a picture post or a text post. A picture post shows the saved photo. Opening a card shows the full caption, every photo, the reaction emoji with their counts, and the comments. A comment is a reply saved in the same chat, or a reply pulled from that post’s discussion thread. The card also shows the count and the first comment, so the thread is visible before the post is opened.

Photos are served by `GET /api/media`. The file must be a JPEG, PNG, or WebP whose path stays inside `Telegram Desktop/`. That route is public, because an image tag cannot send the Basic Auth header. It does not list the folder and it does not serve any other file type.

`GET /api/health` is public, so a dead process can be seen without a password. Every other `/api` route expects HTTP Basic credentials when `API_BASIC_AUTH_PASSWORD` is set. The same username and password go in `frontend/.env` as `VITE_API_BASIC_AUTH_USERNAME` and `VITE_API_BASIC_AUTH_PASSWORD`.

The running routes are `/api/sentiment`, `/api/trends`, `/api/demographics`, `/api/network`, `/api/rag`, and `/api/datasources`. An earlier specification wrote those paths with the component letter attached. The implementation uses the shorter names above. Say so if a reviewer is holding the older note.

There is no eighth page. Report export was cut. The briefs in `docs/review/` are documents for the team, produced from HTML, not a feature of the website.

## 12. Models and the 4 GB limit

| Piece | Approximate weight | When it is loaded |
| --- | --- | --- |
| Sentiment model | 1.1 GB | First, then released |
| Emotion model | 500 MB | Second, then released |
| DistilBART stance | 260 MB | Third, then released |
| MiniLM embeddings | 470 MB | Themes and Ask |
| Ollama `llama3.2:3b`, 4-bit | 2.0 GB | Only while an offline answer is being written |
| Postgres, Redis, API, website | about 2.5–3.5 GB of system RAM | While the demo is open |

Loading the transformers together exceeds 4 GB and kills the demo. The pipeline is a worker-level sequence, not one model instance per HTTP request. `DEVICE=cuda` is the reference setting. `DEVICE=cpu` is the fallback. The large BART stance model stays out of the running process.

Theme clustering also uses UMAP, HDBSCAN, and scikit-learn. The graph uses NetworkX. None of those is a trained classifier for this project.

## 13. Configuration

Copy `.env.example` to `.env`. The database defaults match `docker-compose.yml`.

| Variable | Role |
| --- | --- |
| `DATABASE_URL`, `DATABASE_SYNC_URL` | Async and sync SQLAlchemy URLs. Default database `socmint` on port 5432. |
| `REDIS_URL`, `CELERY_BROKER_URL` | Redis on port 6379 |
| `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, `TELEGRAM_PHONE_NUMBER` | Live reader only. Obtained from the Telegram developer portal. Leave blank for the offline demo. |
| `TELEGRAM_SESSION_NAME` | Session file name. Default `socmint_session`. The file is gitignored. |
| `DEVICE` | `cuda` or `cpu` |
| `SENTIMENT_MODEL`, `EMOTION_MODEL`, `STANCE_MODEL`, `EMBEDDING_MODEL` | The four locked checkpoints |
| `LLM_PROVIDER`, `OLLAMA_MODEL` | Who writes Ask answers |
| `DEMO_B_BATCH_SIZE` | Review cap. Default 50. |
| `BERTOPIC_MAX_DOCS` | Theme cap. Default 500. |
| `STANCE_CONFIDENCE_THRESHOLD` | 0.60 |
| `RAG_COSINE_CUTOFF` | 0.65 |
| `CIB_ANOMALY_THRESHOLD` | 0.70 |
| `MIN_CLUSTER_SIZE`, `DEMO_MIN_CLUSTER_SIZE` | 50 for the research line, 15 for a small demo card |
| `API_BASIC_AUTH_USERNAME`, `API_BASIC_AUTH_PASSWORD` | Dashboard login. Empty password turns the check off for local development. |

Do not commit `.env`, `frontend/.env`, `*.session`, or the `Telegram Desktop/` media folder.

## 14. How to run it

From the project root in PowerShell.

**Install.**

```powershell
Copy-Item .env.example .env
docker compose up -d
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
```

**Review path, no Telegram.**

```powershell
python -m ingestion_a.backfill --offline
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). Interactive API documentation is at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

`scripts/start_system.ps1` checks that PostgreSQL is listening, aligns the seed into the active 48-hour window, and starts the API and the website in two further terminals.

**Offline answers.**

```powershell
ollama serve
ollama pull llama3.2:3b
```

Set `LLM_PROVIDER=ollama`. If Ollama is not running, Ask still returns the retrieved extract.

**Optional live reader.**

```powershell
python -m ingestion_a.download_latest
python -m ingestion_a.download_latest --middle-east
python -m ingestion_a.download_latest --indian-defence
python -m ingestion_a.download_latest --comments
python -m ingestion_a.import_exported --import-all-dirs "Telegram Desktop" --max-posts 80
```

Only one live client may be open. A second process locks the session file.

**After the exam.**

```powershell
psql -U postgres -d socmint -f scripts/post_viva_scrub.sql
```

## 15. A two-minute demonstration

1. Overview. Open one picture post and one text post. The reaction chips are the emoji under the post. The comments are replies, not a second analysis. The counts below are saved posts and posts still waiting to be read.
2. Sources. Collection only stores.
3. Sentiment. The bars are the wording. The reaction row is separate. Sarcasm warns. It does not flip the label.
4. Audience. This is a sketch of the group. If the count is under 50, say that it is below the privacy line.
5. Trends. This cluster is faster in the second half of the window. The words were extracted.
6. Network. Lines are forwards, replies, and mentions. A mark at 0.70 does not name an operator.
7. Ask. Use one prepared question and point at the passages under the answer.

If Telegram is unreachable in the room, stay on the seed. The review does not need the live account.

## 16. What is finished, and what is not

Finished for this review: the schema and migrations, the offline seed, export import, the live reader with photos, paged history, and flood-wait handling, the sequential reader, the reaction score, the audience guard and the IST hour chart, theme velocity, the three-signal graph, grounded Ask with a query log, Basic Auth, the seven pages, the overview post reader (picture lane, text lane, reactions, and comments), and the review briefs.

Not finished, and not to be claimed:

- The Phase 5 comparison against a labelled coordination file. No precision, recall, or F1.
- A statement that every pending post in the database has been read. Pending rows stay pending until B runs. A photograph with no caption stays pending, and it still appears on Overview.
- A statement that the live pull has saved every matching channel, or the full history of every Middle East channel. The reader can be paused and resumed. Indian defence channels were taken at the 80-message cap.
- Discussion comments for the whole archive. `--comments` covers the newest 48 posts, at most 25 replies each. A channel with no linked discussion contributes no thread.
- A 15–25 second timing on CPU, or on a batch larger than 50 posts.
- Validation of the age bands against a census. They are keyword hints.

## 17. Difficulties that changed the design

These are the problems worth explaining, because each one is visible in the code.

| What happened | What the project does about it |
| --- | --- |
| All models together exceed 4 GB | One model is loaded, the batch finishes, the card is freed, and the next model loads |
| The GPU is not always the device in use | The review button stays capped at 50 posts. The timing claim stays attached to the reference GPU |
| Telegram flood waits | One client, a pause between chats, and a sleep for the exact wait Telegram returns |
| The native Telegram cipher did not build on this Windows machine | Pyrofork falls back to its pure-Python cipher. Collection is slower. It still saves messages |
| Two clients and one session file | Ingestion concurrency stays at 1 |
| A review room without a stable network | The offline seed is the product. Live Telegram and an online writer are optional |
| Decorative channel titles failed a keyword test | Titles are folded to plain letters before the subject check |
| A short word matched an unrelated title | Blocked words are matched as whole words |
| The same audience card appeared three times | The page keeps the newest snapshot of each label |
| New downloads were missing on Sentiment | They stay pending until B runs, and the next run reads the newest message times first. Overview shows them immediately, with the photo |
| An image tag cannot send the login header | `GET /api/media` is public, and it only serves an image file inside `Telegram Desktop/` |
| Channel comments are not in the channel history | `--comments` reads the linked discussion and stores each reply under the parent post |
| The audience hour chart was a fixed ratio | The 24 bars and the four parts of the day are counted from `posted_at` in IST |
| Real groups were smaller than 50 accounts | The research line stays 50. A smaller demo card has to be described as below the line |
| A language model will invent an answer from nothing | Search first. Distance beyond 0.65 aborts the question |

## 18. Review briefs

The briefs are handouts. Regenerating them does not change the dashboard.

| Document | Path |
| --- | --- |
| The whole project, in plain words | [docs/review/Whole_Project_Plain_Words.pdf](docs/review/Whole_Project_Plain_Words.pdf) |
| Stack, data sources, and build notes | [docs/review/Stack_Data_and_Challenges.pdf](docs/review/Stack_Data_and_Challenges.pdf) |
| Component A, collection | [docs/review/Component_A_Ingestion.pdf](docs/review/Component_A_Ingestion.pdf) |
| Component B, sentiment, emotion, and stance | [docs/review/Component_B_Sentiment.pdf](docs/review/Component_B_Sentiment.pdf) |
| Component C, audience | [docs/review/Component_C_Audience.pdf](docs/review/Component_C_Audience.pdf) |
| Component D, themes and speed | [docs/review/Component_D_Trends.pdf](docs/review/Component_D_Trends.pdf) |
| Component E, network | [docs/review/Component_E_Network.pdf](docs/review/Component_E_Network.pdf) |

```powershell
.\.venv\Scripts\python.exe docs\review\build_review_pdfs.py
```

## 19. Specification documents

These are the locked design notes. Where this README describes the running code, and an older note describes a route name or a frontend library that was not adopted, the running code is the one to demonstrate.

- [PROJECT_BRIEF.md](PROJECT_BRIEF.md) — scope, locked decisions, and the semester plan
- [ARCHITECTURE.md](ARCHITECTURE.md) — components, tables, and numerical limits
- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) — week-by-week plan
- [docs/EXECUTION_NEXT_STEPS.md](docs/EXECUTION_NEXT_STEPS.md) — what is still open before the exam
