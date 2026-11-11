"""Build five second-review briefs, one per agent, as print-ready HTML."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
HTML = ROOT / "html"

CSS = """
@page { size: A4; margin: 16mm 15mm 18mm; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: "Segoe UI", Calibri, sans-serif;
  color: #1a1a1a;
  font-size: 11pt;
  line-height: 1.45;
}
header.banner {
  background: #1f4fff;
  color: white;
  padding: 14px 18px 12px;
  margin: -2px 0 16px;
}
header.banner .kicker {
  margin: 0;
  font-size: 9pt;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  opacity: 0.9;
}
header.banner h1 {
  margin: 4px 0 0;
  font-size: 22pt;
  line-height: 1.05;
  font-weight: 700;
}
header.banner p { margin: 6px 0 0; font-size: 10.5pt; }
h2 {
  font-size: 13pt;
  margin: 18px 0 6px;
  padding-bottom: 3px;
  border-bottom: 2px solid #1f4fff;
}
h3 { font-size: 11.5pt; margin: 12px 0 4px; }
p { margin: 6px 0; }
ul, ol { margin: 6px 0 8px; padding-left: 18px; }
li { margin: 2px 0; }
.note, .warn, .say {
  border: 1px solid #d9d9d9;
  padding: 8px 12px;
  margin: 10px 0;
  background: #f7f8fb;
}
.warn { border-left: 4px solid #c2410c; background: #fff8f3; }
.say { border-left: 4px solid #1f4fff; }
table { width: 100%; border-collapse: collapse; margin: 8px 0 12px; font-size: 10pt; }
th, td { border: 1px solid #d0d0d0; padding: 5px 7px; vertical-align: top; text-align: left; }
th { background: #eef2ff; font-weight: 650; }
code { font-family: Consolas, monospace; font-size: 9.5pt; background: #f3f4f6; padding: 0 3px; }
.figure { margin: 10px 0 14px; page-break-inside: avoid; }
.figure svg { width: 100%; height: auto; }
.caption { font-size: 9pt; color: #444; margin-top: 3px; }
footer {
  margin-top: 18px;
  font-size: 8.5pt;
  color: #555;
  border-top: 1px solid #ddd;
  padding-top: 6px;
}
"""

SYSTEM = """
<svg viewBox="0 0 720 168" xmlns="http://www.w3.org/2000/svg" role="img">
  <rect x="8" y="18" width="110" height="52" fill="#1f4fff"/>
  <text x="63" y="48" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">A Ingestion</text>
  <rect x="150" y="18" width="130" height="52" fill="#111"/>
  <text x="215" y="42" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">PostgreSQL</text>
  <text x="215" y="58" text-anchor="middle" fill="#d6ff3f" font-size="10" font-family="Segoe UI">raw posts</text>
  <rect x="312" y="8" width="120" height="36" fill="#eef2ff" stroke="#1f4fff"/>
  <text x="372" y="31" text-anchor="middle" font-size="12" font-family="Segoe UI">B per post</text>
  <rect x="312" y="52" width="120" height="28" fill="#fff" stroke="#111"/>
  <text x="372" y="70" text-anchor="middle" font-size="11" font-family="Segoe UI">C window</text>
  <rect x="448" y="52" width="120" height="28" fill="#fff" stroke="#111"/>
  <text x="508" y="70" text-anchor="middle" font-size="11" font-family="Segoe UI">D window</text>
  <rect x="584" y="52" width="120" height="28" fill="#fff" stroke="#111"/>
  <text x="644" y="70" text-anchor="middle" font-size="11" font-family="Segoe UI">E window</text>
  <rect x="400" y="108" width="200" height="40" fill="#111"/>
  <text x="500" y="133" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">Ask: search, then one answer</text>
  <path d="M118 44 H150" stroke="#111" stroke-width="1.5"/>
  <path d="M280 44 H312" stroke="#111" stroke-width="1.5"/>
  <path d="M372 88 V108" stroke="#111" stroke-width="1.2"/>
</svg>
<p class="caption">Figure 1. Posts land in Postgres. B reads one post at a time. C, D, and E recompute a time window. Ask searches the short summaries those agents write.</p>
"""


def page(title: str, subtitle: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<title>{title}</title>
<style>{CSS}</style></head><body>
<header class="banner">
  <p class="kicker">Second review · academic prototype · not an operational system</p>
  <h1>{title}</h1>
  <p>{subtitle}</p>
</header>
{body}
<footer>AI-Driven Social Media Audience Intelligence Framework · 7th semester CSE minor project · Public Telegram only · Figures describe the implemented design.</footer>
</body></html>
"""


DOCS: dict[str, tuple[str, str, str]] = {}

DOCS["Component_A_Ingestion"] = (
    "Component A — Ingestion",
    "How public Telegram posts get into the database, and how the demo still works offline.",
    f"""
<div class="note">This brief is for the teammate who presents collection. The exam path is the offline seed. Live Telegram is extra and can fail on campus Wi-Fi or Telegram rate limits.</div>
<h2>1. What this agent does</h2>
<p>Component A collects public Telegram posts and stores them once. It does not decide whether a post is positive, topical, or coordinated. It only records the message, the channel, the time the message was posted, and any photo that was saved.</p>
<p>The National Technical Research Organisation name is the origin of the public problem statement. This software is an undergraduate prototype. It is not an operational intelligence system.</p>
<h2>2. Where it sits</h2>
<div class="figure">{SYSTEM}</div>
<h2>3. Three ways a post can arrive</h2>
<table>
<tr><th>Path</th><th>When to use it</th><th>What it does</th></tr>
<tr><td>Offline seed<br><code>ingestion_a/backfill.py --offline</code></td><td>The viva, and any room without internet</td><td>Replays a prepared set of posts into Postgres. This is the path that must work.</td></tr>
<tr><td>Desktop export<br><code>ingestion_a/import_exported.py</code></td><td>When a chat was exported from Telegram Desktop</td><td>Reads the export and inserts posts. Message id plus channel slug prevents duplicates.</td></tr>
<tr><td>Live client<br>Pyrofork, <code>download_latest</code></td><td>Optional demonstration only</td><td>Reads public channels, saves up to 80 recent messages, and stores photos under <code>Telegram Desktop</code>.</td></tr>
</table>
<h2>4. How a live pull works</h2>
<ol>
<li>One worker only. A second client would lock the Telegram session file.</li>
<li>Channels are read with a pause and a small random wait, so Telegram is less likely to block the account.</li>
<li>If Telegram returns a flood wait, the client sleeps for the time Telegram demands, then continues.</li>
<li>Each saved row uses <code>posted_at</code> for the message time. <code>ingested_at</code> is only when our program stored it. Later agents must use <code>posted_at</code>.</li>
<li>If the same message is imported again, the text time is kept. Photos and reaction counts can be updated.</li>
</ol>
<div class="figure">
<svg viewBox="0 0 720 78" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="140" height="44" fill="#1f4fff"/><text x="78" y="43" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Public channel</text>
  <rect x="180" y="16" width="150" height="44" fill="#111"/><text x="255" y="43" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">One session</text>
  <rect x="362" y="16" width="160" height="44" fill="#eef2ff" stroke="#1f4fff"/><text x="442" y="43" text-anchor="middle" font-size="13" font-family="Segoe UI">raw_posts</text>
  <rect x="554" y="16" width="150" height="44" fill="#fff" stroke="#111"/><text x="629" y="43" text-anchor="middle" font-size="13" font-family="Segoe UI">status: pending</text>
  <path d="M148 38 H180 M330 38 H362 M522 38 H554" stroke="#111" stroke-width="1.4"/>
</svg>
<p class="caption">Figure 2. A new post is stored as pending. Component B is the only agent that later marks it processed.</p>
</div>
<h2>5. What is stored</h2>
<table>
<tr><th>Table</th><th>Holds</th></tr>
<tr><td><code>monitored_channels</code></td><td>Channel name, topic tags, last check.</td></tr>
<tr><td><code>raw_posts</code></td><td>Text, photo path, view count, reaction counts, <code>posted_at</code>, processing status.</td></tr>
<tr><td><code>raw_authors</code></td><td>Public display name and bio snapshot when a discussion author is visible. No private profile scrape.</td></tr>
</table>
<h2>6. What to show</h2>
<p>Open <strong>Sources</strong>. It lists channels, how many posts are saved, and the last check. Say: “Collection writes rows. It does not analyse them.” Then show one photo path if a reviewer asks where images go: the <code>Telegram Desktop</code> folder, with the path also stored on the post.</p>
<div class="say"><strong>One sentence.</strong> “We store the public post and the time Telegram gave it. Analysis is a later step, so a dead network cannot erase the demo.”</div>
<h2>7. Related parts you may be asked about</h2>
<table>
<tr><th>Part</th><th>Relation to A</th></tr>
<tr><td>Orchestrator</td><td>Does not collect. It tells B to read pending rows, then tells C, D, and E to recompute a window.</td></tr>
<tr><td>Dashboard</td><td>Sources is view A. Overview counts saved posts and posts still waiting.</td></tr>
<tr><td>Ask</td><td>Does not read raw posts directly. It searches short summaries written after analysis.</td></tr>
<tr><td>Privacy</td><td>The design is public channels. A post-viva SQL script clears message text and display names.</td></tr>
</table>
<h2>8. Done, and not done</h2>
<table>
<tr><th>Done</th><th>Not for this review</th></tr>
<tr><td>Schema, offline replay, export import, live client with photo save and flood-wait sleep.</td><td>A full history of every channel. The live pull is capped at 80 messages and was paused.</td></tr>
<tr><td>Duplicate protection by platform message id.</td><td>No forensic hash, no deletion tracking. Both were left out of the brief on purpose.</td></tr>
</table>
<div class="warn"><strong>Do not claim</strong> that every chat on the phone has been downloaded, or that the live path is required for the exam.</div>
<h2>9. Likely questions</h2>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>Why not the download time?</td><td>Download time measures our delay. Topic speed and coordination use <code>posted_at</code>.</td></tr>
<tr><td>Why one worker?</td><td>The Telegram session file is a single SQLite file. Two workers corrupt or lock it.</td></tr>
<tr><td>Why did a live run stop?</td><td>Telegram asked the account to wait. The client sleeps. That is rate limiting, not a crash.</td></tr>
</table>
""",
)

DOCS["Component_B_Sentiment"] = (
    "Component B — Sentiment, emotion, and stance",
    "How one post is read for feeling, emotion, stance, sarcasm, and the reaction bar.",
    f"""
<div class="note">This brief is for the teammate who presents the reading of each post. The models are used as published. We did not train them.</div>
<h2>1. What this agent does</h2>
<p>Component B reads the text of one post and writes one result row. It also scores the emoji reaction bar under the post. Those two readings stay separate. A crowd of likes does not rewrite the text label.</p>
<h2>2. Where it sits</h2>
<div class="figure">{SYSTEM}</div>
<p>B is the only row runner. A post starts as <code>pending</code>. After B, it is <code>processed</code>. C, D, and E do not wait for that flag. They read a time window of posts.</p>
<h2>3. The four readings</h2>
<table>
<tr><th>Reading</th><th>Method</th><th>Output</th></tr>
<tr><td>Sentiment</td><td><code>cardiffnlp/twitter-xlm-roberta-base-sentiment</code></td><td>positive, neutral, or negative</td></tr>
<tr><td>Emotion</td><td><code>SamLowe/roberta-base-go_emotions</code>, mapped to Ekman emotions plus neutral</td><td>joy, anger, sadness, fear, disgust, surprise, neutral</td></tr>
<tr><td>Stance</td><td><code>valhalla/distilbart-mnli-12-3</code> against the channel topic</td><td>supportive, against, neutral, or unclear</td></tr>
<tr><td>Sarcasm</td><td>Rules on text and emoji. No neural model.</td><td>A flag only. The sentiment label stays as the model gave it.</td></tr>
<tr><td>Reaction bar</td><td>Count of 👍 🔥 and similar marks versus 👎 🤡 and similar marks</td><td>A separate score. Cutoff 0.15. Unmapped emoji do not move it.</td></tr>
</table>
<h2>4. Why the models run one after another</h2>
<p>The reference laptop has a 4 GB graphics card. Loading sentiment, emotion, and stance together exceeds that budget. The pipeline loads one model, finishes the batch, releases it, then loads the next. On a machine without a usable GPU the same order runs on the CPU. It is slower. The labels do not change because the device changed.</p>
<div class="figure">
<svg viewBox="0 0 720 70" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="14" width="150" height="40" fill="#1f4fff"/><text x="83" y="39" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">1 Sentiment</text>
  <rect x="190" y="14" width="150" height="40" fill="#1f4fff"/><text x="265" y="39" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">2 Emotion</text>
  <rect x="372" y="14" width="150" height="40" fill="#1f4fff"/><text x="447" y="39" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">3 Stance</text>
  <rect x="554" y="14" width="150" height="40" fill="#111"/><text x="629" y="39" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">4 Rules</text>
  <path d="M158 34 H190 M340 34 H372 M522 34 H554" stroke="#111" stroke-width="1.4"/>
</svg>
<p class="caption">Figure 2. Memory is cleared between the three neural models. Sarcasm and the reaction bar need no graphics memory.</p>
</div>
<h2>5. Stance rule</h2>
<p>DistilBART asks whether the text supports or opposes the channel topic. If the best score is under 0.60, the stance is neutral or unclear. We do not force a side. The larger BART model is only a comparison for the report. It is not loaded in the demo, because it is about 1.6 GB.</p>
<h2>6. What to show</h2>
<p>Open <strong>Sentiment</strong>. Point at the positive, neutral, and negative bars, then at the reaction chips. Say the reaction row is the audience tapping the post, and the bars are the text model.</p>
<div class="say"><strong>One sentence.</strong> “Sarcasm lowers our confidence. It never turns a positive label into a negative one.”</div>
<h2>7. Related parts</h2>
<table>
<tr><th>Part</th><th>Relation to B</th></tr>
<tr><td>Run analysis</td><td>The button sends at most 50 pending posts through B, then refreshes C, D, and E. That cap is the viva timing budget, not the size of the archive.</td></tr>
<tr><td>Table</td><td><code>sentiment_results_b</code>, one row per post.</td></tr>
<tr><td>API</td><td><code>GET /api/sentiment/timeline</code></td></tr>
<tr><td>Ask</td><td>B’s short summary can be retrieved later. The raw post is not the search document.</td></tr>
</table>
<h2>8. Done, and not done</h2>
<table>
<tr><th>Done</th><th>Not claimed</th></tr>
<tr><td>Sequential pipeline, stance threshold, sarcasm flag, reaction score, Sentiment page.</td><td>No accuracy percentage. SemEval comparison is Phase 5 and has not been run.</td></tr>
<tr><td>Empty text is skipped. A photo with no words cannot be given a text sentiment.</td><td>Not every newly downloaded post has been through B yet. Pending rows stay pending until a run.</td></tr>
</table>
<div class="warn"><strong>Do not say</strong> “98 percent accurate”, and do not say the reaction bar is the sentiment.</div>
<h2>9. Likely questions</h2>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>Did you train the model?</td><td>No. These are public Hugging Face checkpoints used off the shelf.</td></tr>
<tr><td>Why DistilBART?</td><td>About 260 MB. The large MNLI model does not fit the 4 GB card beside the others.</td></tr>
<tr><td>Why is a new channel missing?</td><td>A is storage. B has not been run on those pending rows yet.</td></tr>
</table>
""",
)

DOCS["Component_C_Audience"] = (
    "Component C — Audience",
    "How the prototype describes a group of accounts without profiling a person.",
    f"""
<div class="note">This brief is for the teammate who presents audience. The output is a coarse guess from public text and posting time. It is not a census.</div>
<h2>1. What this agent does</h2>
<p>Component C summarises who appears to be talking in a time window: rough age bands, rough region, language, interests, and when posts arrive in India Standard Time. It works on groups. It does not open a page for one named person and assign them an age.</p>
<h2>2. Where it sits</h2>
<div class="figure">{SYSTEM}</div>
<p>C runs on a window, usually 48 hours of <code>posted_at</code>. It recomputes that window. It does not update one account in place all day.</p>
<h2>3. Two layers</h2>
<table>
<tr><th>Layer</th><th>What is visible</th><th>What we infer</th></tr>
<tr><td>Broadcast</td><td>Channel name, topic tags, hours when posts appear</td><td>A coarse interest and a daily rhythm</td></tr>
<tr><td>Discussion</td><td>Public display name and bio text of people who spoke in a linked discussion</td><td>Keyword hints for age band, region, and interest</td></tr>
</table>
<p>Telegram does not give us a subscriber list. Anyone who never speaks is invisible. Say that before a reviewer treats the chart as the whole audience.</p>
<h2>4. The privacy line</h2>
<p>The locked rule is k-anonymity with k at least 50. A group smaller than 50 accounts is marked <code>below_threshold</code>. The production guard uses 50. A demo run can use 15 so a small seed still produces a card. The card must be described as below the research threshold, not as a reliable demographic.</p>
<div class="warn">The current Audience page can show a small group because a demo run saved one. In the review, say the guard exists and the number on screen is below 50, so it is illustrative, not a finding about a population.</div>
<h2>5. What is written</h2>
<table>
<tr><th>Field</th><th>Meaning</th></tr>
<tr><td><code>account_count</code></td><td>How many accounts were in the group.</td></tr>
<tr><td>Age, geography, language, interest</td><td>Shares that sum as distributions, not a label on one user.</td></tr>
<tr><td><code>below_threshold</code></td><td>True when the group is too small.</td></tr>
<tr><td><code>analyzed_at</code></td><td>When this snapshot was computed. Each run inserts a new snapshot.</td></tr>
</table>
<p>The API keeps the newest snapshot for each group label, so the page does not stack three copies of the same run.</p>
<h2>6. What to show</h2>
<p>Open <strong>Audience</strong>. Explain the clock first: morning, afternoon, evening in IST, computed from <code>posted_at</code>. Then the group card. If the count is under 50, say so out loud.</p>
<div class="say"><strong>One sentence.</strong> “This is a keyword sketch of public speakers in the window. It is not an identity record.”</div>
<h2>7. Related parts</h2>
<table>
<tr><th>Part</th><th>Relation to C</th></tr>
<tr><td>Table</td><td><code>demographic_aggregates_c</code></td></tr>
<tr><td>API</td><td><code>GET /api/demographics</code></td></tr>
<tr><td>Ask</td><td>Can quote the group summary. It should not invent a person’s age.</td></tr>
<tr><td>After the exam</td><td><code>scripts/post_viva_scrub.sql</code> clears bios and display names.</td></tr>
</table>
<h2>8. Done, and not done</h2>
<table>
<tr><th>Done</th><th>Not claimed</th></tr>
<tr><td>Heuristic distributions, threshold flag, Audience page, IST rhythm.</td><td>No individual dossier. No claim that the age bands were validated against a census.</td></tr>
</table>
<h2>9. Likely questions</h2>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>How do you know someone is 25 to 34?</td><td>We do not know. A keyword in a public bio can place the account in a band. Many bios say nothing, so the band is a weak prior.</td></tr>
<tr><td>Why show a group of 8?</td><td>The demo threshold is lower so the screen is not empty. The research line remains 50. Eight is below it.</td></tr>
<tr><td>Why three identical cards before?</td><td>Each analysis run saved another copy. The page now keeps the latest copy of each label.</td></tr>
</table>
""",
)

DOCS["Component_D_Trends"] = (
    "Component D — Topics and speed",
    "How posts in a window become themes, and which themes are speeding up.",
    f"""
<div class="note">This brief is for the teammate who presents topics. A theme is a cluster of similar posts. Speed is posts per hour, using the time the message was posted.</div>
<h2>1. What this agent does</h2>
<p>Component D groups recent posts into themes and ranks those themes by how fast they are being posted, and by whether that speed is rising or falling. It does not decide who is coordinated. That is Component E.</p>
<h2>2. Where it sits</h2>
<div class="figure">{SYSTEM}</div>
<p>D recomputes the whole window each time. At this project’s size, a few hundred to a few thousand posts, a full recompute is simpler than an incremental topic model and is what the brief locks.</p>
<h2>3. How a theme is made</h2>
<ol>
<li>Take posts in the window that have text. The clock is <code>posted_at</code>.</li>
<li>Embed each post with <code>paraphrase-multilingual-MiniLM-L12-v2</code>. The same model embeds Ask queries. Dimension 384.</li>
<li>Cluster with BERTopic and HDBSCAN. Minimum topic size is 3, so a tiny corpus can still form a theme.</li>
<li>Cap the run at 500 documents so memory stays bounded.</li>
<li>Name the theme from its distinctive words.</li>
</ol>
<h2>4. Speed and change</h2>
<p>Split the window in half. Velocity is posts per hour across the whole window. Acceleration compares the second half with the first. Positive acceleration is the “rising” mark on the Trends page. Negative acceleration means the theme is cooling. Neither number is a prediction of tomorrow.</p>
<table>
<tr><th>Symbol</th><th>Plain meaning</th></tr>
<tr><td>v</td><td>Posts in the theme, divided by hours in the window.</td></tr>
<tr><td>a</td><td>How much v changed from the first half of the window to the second.</td></tr>
<tr><td>Rising</td><td>a is above zero.</td></tr>
</table>
<div class="figure">
<svg viewBox="0 0 720 86" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="22" width="220" height="40" fill="#eef2ff" stroke="#1f4fff"/><text x="118" y="47" text-anchor="middle" font-size="13" font-family="Segoe UI">First half of 48 h</text>
  <rect x="250" y="22" width="220" height="40" fill="#1f4fff"/><text x="360" y="47" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Second half</text>
  <rect x="492" y="22" width="210" height="40" fill="#111"/><text x="597" y="47" text-anchor="middle" fill="#d6ff3f" font-size="13" font-family="Segoe UI">Rising if faster</text>
</svg>
<p class="caption">Figure 2. A theme is rising only if it is posted faster in the later half than in the earlier half.</p>
</div>
<h2>5. What to show</h2>
<p>Open <strong>Trends</strong>. Read one theme name, its posts per hour, and whether it is rising. Say the words in the theme are extracted terms, not a headline written by a person.</p>
<div class="say"><strong>One sentence.</strong> “We measure how fast a cluster of similar posts is arriving, on the clock Telegram stamped, not on the clock we downloaded them.”</div>
<h2>6. Related parts</h2>
<table>
<tr><th>Part</th><th>Relation to D</th></tr>
<tr><td>Table</td><td><code>trend_topics_d</code></td></tr>
<tr><td>API</td><td><code>GET /api/trends</code>. The page shows the latest run in the window, not every past run stacked together.</td></tr>
<tr><td>Ask</td><td>Can cite a topic summary. If nothing is close enough, Ask refuses instead of inventing a theme.</td></tr>
<tr><td>B</td><td>Not required. D clusters raw text. Sentiment is a different page.</td></tr>
</table>
<h2>7. Done, and not done</h2>
<table>
<tr><th>Done</th><th>Not claimed</th></tr>
<tr><td>BERTopic path, 500-document cap, velocity and acceleration, Trends page.</td><td>No manual theme-quality study yet. That is Phase 5. A theme can be messy when the window is small.</td></tr>
</table>
<div class="warn"><strong>Do not say</strong> the model “understood the news”. It grouped similar wording and counted speed.</div>
<h2>8. Likely questions</h2>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>Why minimum size 3?</td><td>A student corpus is small. A higher minimum would hide every theme.</td></tr>
<tr><td>Why 500?</td><td>BERTopic embeddings spike memory. The cap is a hardware limit, stated in the brief.</td></tr>
<tr><td>Why did topics not change after a download?</td><td>D writes a snapshot when analysis runs. New posts sit in the database until the next window run.</td></tr>
</table>
""",
)

DOCS["Component_E_Network"] = (
    "Component E — Network and coordination screen",
    "How accounts connect, and why a high score is a screen, not an accusation.",
    f"""
<div class="note">This brief is for the teammate who presents the graph. The score is an unweighted average of three behaviour signals. It is not a verdict that an account is a bot or a campaign.</div>
<h2>1. What this agent does</h2>
<p>Component E builds a graph of public interactions: forwards, replies, and mentions. It finds communities, finds accounts that sit between communities, and computes a screening score for similar posting behaviour.</p>
<h2>2. Where it sits</h2>
<div class="figure">{SYSTEM}</div>
<p>E recomputes a window. Edges are directed, because a forward has a direction. Community detection needs an undirected copy of that graph. The code makes a real copy, not a view, then runs Louvain. The import is <code>import community</code> from the package <code>python-louvain</code>.</p>
<h2>3. The picture the page draws</h2>
<table>
<tr><th>On screen</th><th>Meaning</th></tr>
<tr><td>Node</td><td>A channel or a public author.</td></tr>
<tr><td>Line</td><td>A forward, reply, or mention.</td></tr>
<tr><td>Size</td><td>Betweenness: how often the account sits on paths between others.</td></tr>
<tr><td>Colour groups</td><td>Louvain communities on the undirected copy.</td></tr>
<tr><td>Red ring</td><td>The screening score is at least 0.70.</td></tr>
</table>
<p>The API returns at most 500 nodes, the ones with the highest betweenness. Edges are only those whose both ends are in that set. That keeps the canvas from drawing dangling lines.</p>
<h2>4. The three signals</h2>
<table>
<tr><th>Signal</th><th>Question it asks</th></tr>
<tr><td>Posting synchrony</td><td>Do this account’s posts land within two minutes of other posts unusually often?</td></tr>
<tr><td>Age and volume</td><td>Is a young account posting a lot? Missing creation dates weaken this signal.</td></tr>
<tr><td>Duplicate content</td><td>Is the text unusually similar to other texts in the window? Similarity uses TF-IDF, not the neural embedder.</td></tr>
</table>
<p>The score is <code>(s1 + s2 + s3) / 3</code>. There are no learned weights. A flag is raised at 0.70. Both choices are locked so the review can be explained on a whiteboard.</p>
<div class="figure">
<svg viewBox="0 0 720 78" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="150" height="44" fill="#eef2ff" stroke="#1f4fff"/><text x="83" y="42" text-anchor="middle" font-size="12" font-family="Segoe UI">Synchrony</text>
  <rect x="176" y="16" width="150" height="44" fill="#eef2ff" stroke="#1f4fff"/><text x="251" y="42" text-anchor="middle" font-size="12" font-family="Segoe UI">Age / volume</text>
  <rect x="344" y="16" width="150" height="44" fill="#eef2ff" stroke="#1f4fff"/><text x="419" y="42" text-anchor="middle" font-size="12" font-family="Segoe UI">Near-copies</text>
  <rect x="520" y="16" width="184" height="44" fill="#111"/><text x="612" y="36" text-anchor="middle" fill="white" font-size="12" font-family="Segoe UI">Average</text>
  <text x="612" y="52" text-anchor="middle" fill="#d6ff3f" font-size="11" font-family="Segoe UI">flag at 0.70</text>
</svg>
<p class="caption">Figure 2. Three equal signals. No signal is allowed to outweigh the others by a trained weight.</p>
</div>
<h2>5. What to show</h2>
<p>Open <strong>Network</strong>. Name one community count and one connector. If the flagged count is zero, say the screen found no account over 0.70 in this window. Zero is a result, not a broken page.</p>
<div class="say"><strong>One sentence.</strong> “A red ring means the three behaviour scores average at least 0.70. It does not name an operator.”</div>
<h2>6. Related parts</h2>
<table>
<tr><th>Part</th><th>Relation to E</th></tr>
<tr><td>Tables</td><td><code>network_nodes_e</code>, <code>network_edges_e</code></td></tr>
<tr><td>API</td><td><code>GET /api/network/graph</code></td></tr>
<tr><td>Ask</td><td>May describe a community summary. It must not upgrade a screen into an attribution.</td></tr>
<tr><td>Phase 5</td><td>An offline coordination file was planned to score two of the three signals. That benchmark has not been run. Do not quote precision or recall.</td></tr>
</table>
<h2>7. Done, and not done</h2>
<table>
<tr><th>Done</th><th>Not claimed</th></tr>
<tr><td>Directed graph, undirected Louvain, three-signal average, 500-node cap, Network page.</td><td>No bot label, no legal finding, no published F1. The offline benchmark is still future work.</td></tr>
</table>
<div class="warn"><strong>Do not say</strong> “we detected a campaign” or “this account is fake”.</div>
<h2>8. Likely questions</h2>
<table>
<tr><th>Question</th><th>Answer</th></tr>
<tr><td>Why undirected Louvain?</td><td>The standard Louvain implementation we use expects an undirected graph. We keep the directed edges for the drawing.</td></tr>
<tr><td>Why equal weights?</td><td>A learned weight would need a labelled set we have not evaluated. An equal average is explainable.</td></tr>
<tr><td>Why is the same channel listed twice sometimes?</td><td>An older run could leave a second snapshot. The page is supposed to keep the latest window. If a duplicate remains, it is a snapshot bug, not two actors.</td></tr>
</table>
""",
)


DOCS["Stack_Data_and_Challenges"] = (
    "Technology stack, data, and build notes",
    "What the prototype is built from, where the posts come from, and what broke along the way.",
    f"""
<div class="note">This brief is shared. It sits beside the five agent briefs. It describes an undergraduate prototype. It is not an operational intelligence system, and it is not deployed by any agency. The public problem statement is the only link to that origin.</div>
<h2>1. How the running system is split</h2>
<p>The laptop runs the website and the API. Docker runs only the two data services. Models are loaded inside the API process, one at a time. A live Telegram client is optional and is not required for the review.</p>
<div class="figure">
<svg viewBox="0 0 720 150" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="18" width="150" height="52" fill="#1f4fff"/>
  <text x="83" y="40" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">React + Vite</text>
  <text x="83" y="56" text-anchor="middle" fill="white" font-size="10" font-family="Segoe UI">port 5173</text>
  <rect x="190" y="18" width="160" height="52" fill="#111"/>
  <text x="270" y="40" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">FastAPI</text>
  <text x="270" y="56" text-anchor="middle" fill="#d6ff3f" font-size="10" font-family="Segoe UI">port 8000</text>
  <rect x="382" y="8" width="160" height="36" fill="#eef2ff" stroke="#1f4fff"/>
  <text x="462" y="31" text-anchor="middle" font-size="12" font-family="Segoe UI">Postgres 16 + vectors</text>
  <rect x="382" y="52" width="160" height="28" fill="#fff" stroke="#111"/>
  <text x="462" y="70" text-anchor="middle" font-size="12" font-family="Segoe UI">Redis</text>
  <rect x="566" y="18" width="142" height="52" fill="#fff" stroke="#1f4fff"/>
  <text x="637" y="40" text-anchor="middle" font-size="12" font-family="Segoe UI">Optional</text>
  <text x="637" y="56" text-anchor="middle" font-size="11" font-family="Segoe UI">Telegram client</text>
  <path d="M158 44 H190 M350 44 H382" stroke="#111" stroke-width="1.4"/>
  <text x="360" y="120" text-anchor="middle" font-size="11" font-family="Segoe UI">The browser talks only to the API. The API talks to Postgres. Redis is there for background jobs.</text>
</svg>
<p class="caption">Figure 1. The website never opens the database itself. Collection, analysis, and Ask all go through the API.</p>
</div>
<h2>2. The stack, and the job each part does</h2>
<table>
<tr><th>Layer</th><th>What we use</th><th>What it does in this project</th></tr>
<tr><td>Language</td><td>Python 3.11</td><td>API, collection, models, and the offline seed.</td></tr>
<tr><td>API</td><td>FastAPI, Pydantic v2, Uvicorn</td><td>Seven data routes plus health. Request bodies are checked before they touch the database.</td></tr>
<tr><td>Auth</td><td>HTTP Basic</td><td>The dashboard sends a lab username and password. The health check stays open so we can see whether the process is up.</td></tr>
<tr><td>Database</td><td>PostgreSQL 16, SQLAlchemy 2.0, Alembic</td><td>Channels, posts, analysis rows, and Ask logs. Migrations create the tables. The first migration also enables the vector extension.</td></tr>
<tr><td>Search</td><td>pgvector</td><td>Stores 384-number embeddings. Ask rejects a question when the nearest summary is farther than cosine distance 0.65.</td></tr>
<tr><td>Jobs</td><td>Celery, Redis 7</td><td>Designed for a slow background cycle: one channel at a time, one ingestion worker. The review button can also run the same analysis immediately.</td></tr>
<tr><td>Containers</td><td>Docker Compose</td><td>Postgres uses the <code>pgvector/pgvector:pg16</code> image. Redis uses <code>redis:7-alpine</code>. The API and the website run on the host, not inside those containers.</td></tr>
<tr><td>Collection</td><td>Pyrofork</td><td>Optional live reader for public Telegram channels and groups. A saved session file is a single SQLite file, so only one client may use it.</td></tr>
<tr><td>Reading posts</td><td>PyTorch, Hugging Face Transformers</td><td>Three published models, loaded one after another: sentiment, emotion, then stance.</td></tr>
<tr><td>Themes and Ask search</td><td>sentence-transformers, BERTopic, HDBSCAN, UMAP</td><td>The same MiniLM model embeds posts for themes and embeds the short summaries Ask searches.</td></tr>
<tr><td>Graph</td><td>NetworkX, python-louvain</td><td>Directed interactions, then an undirected copy for communities. The score is an equal average of three signals.</td></tr>
<tr><td>Written answers</td><td>Local Ollama, or an online model when a key is set</td><td>Search always happens in Postgres first. The language model only writes from the passages that passed the cutoff. Every question and the passages used are logged.</td></tr>
<tr><td>Website</td><td>React 18, Vite 6</td><td>Seven views. Styling is our own CSS. The dev server proxies <code>/api</code> to port 8000.</td></tr>
</table>
<div class="warn">The early design notes mention Tailwind, Recharts, and a force-graph library. Those were not added. The pages draw their own bars and the network canvas. Say that if a reviewer has the older note.</div>
<h2>3. The models, and why they are not all loaded together</h2>
<table>
<tr><th>Job</th><th>Checkpoint</th><th>Rough weight</th></tr>
<tr><td>Sentiment</td><td><code>cardiffnlp/twitter-xlm-roberta-base-sentiment</code></td><td>about 1.1 GB</td></tr>
<tr><td>Emotion</td><td><code>SamLowe/roberta-base-go_emotions</code></td><td>about 500 MB</td></tr>
<tr><td>Stance</td><td><code>valhalla/distilbart-mnli-12-3</code></td><td>about 260 MB</td></tr>
<tr><td>Embeddings</td><td><code>paraphrase-multilingual-MiniLM-L12-v2</code></td><td>about 470 MB</td></tr>
<tr><td>Offline answer model</td><td>Ollama <code>llama3.2:3b</code>, 4-bit</td><td>about 2 GB</td></tr>
</table>
<p>The reference card is a GTX 1650 Ti with 4 GB. Those weights do not fit together. The pipeline loads one model, finishes the batch, frees the card, then loads the next. We did not train any of them. The large BART stance model, about 1.6 GB, is a report comparison only and is not loaded in the demo. If the card is unavailable, the same code runs on the CPU. The labels do not change. The run takes longer, so we do not promise a 15–25 second demo on CPU or on thousands of posts. That timing is only for a batch of at most 50 posts on the reference GPU.</p>
<h2>4. Where the posts come from</h2>
<p>There are three sources. They all land in the same tables. A repeated message is recognised by its channel and message id, so a second import does not create a second row or wipe an analysis that already ran.</p>
<table>
<tr><th>Source</th><th>Command</th><th>When we use it</th></tr>
<tr><td>Offline seed</td><td><code>python -m ingestion_a.backfill --offline</code></td><td>The review and any room without a stable network. Prepared posts are given recent times so the 48-hour pages are not empty. Extra posts can be generated from written templates. No Telegram call is made.</td></tr>
<tr><td>Desktop export</td><td><code>python -m ingestion_a.import_exported</code></td><td>Chats exported from Telegram Desktop as HTML (<code>messages.html</code>) or JSON (<code>result.json</code>). The importer reads the channel name, message id, text, time, and reaction counts.</td></tr>
<tr><td>Live reader</td><td><code>python -m ingestion_a.download_latest</code></td><td>Optional. Public channels and groups whose titles match the project subjects: geopolitics, strategy, conflict, defence, OSINT, space, cybersecurity, politics, governance, and development. Latest 80 messages. Photos only, saved under <code>Telegram Desktop</code>.</td></tr>
</table>
<div class="figure">
<svg viewBox="0 0 720 92" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="150" height="48" fill="#1f4fff"/><text x="83" y="44" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Offline seed</text>
  <rect x="176" y="16" width="160" height="48" fill="#111"/><text x="256" y="44" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Desktop export</text>
  <rect x="354" y="16" width="150" height="48" fill="#eef2ff" stroke="#1f4fff"/><text x="429" y="44" text-anchor="middle" font-size="13" font-family="Segoe UI">Live reader</text>
  <rect x="528" y="16" width="180" height="48" fill="#fff" stroke="#111"/><text x="618" y="38" text-anchor="middle" font-size="13" font-family="Segoe UI">raw_posts</text><text x="618" y="54" text-anchor="middle" font-size="11" font-family="Segoe UI">one row per message</text>
  <path d="M158 40 H176 M336 40 H354 M504 40 H528" stroke="#111" stroke-width="1.4"/>
</svg>
<p class="caption">Figure 2. Three doors, one table. The time used later is the time on the message, not the time we stored the row.</p>
</div>
<p>The live reader keeps a title only when it matches the subject list. Unrelated exports — books, films, job posts, cracked software — are left out. A title written in decorative Unicode is folded to plain letters before that check, otherwise a real channel can look like a random string. The reader sleeps when Telegram asks it to wait, then continues the same chat. The live pull was paused before every matching chat had been saved. The review does not depend on finishing it.</p>
<p>What a stored post holds: text, the message time, view count, reaction counts, a photo path when a picture was saved, and a status of pending or processed. Display names and bios are stored only when a person actually spoke in a public discussion. Subscriber lists are not available, and private one-to-one chats are not the collection design. After the exam, <code>scripts/post_viva_scrub.sql</code> clears message text, display names, and bios.</p>
<h2>5. Challenges, and what we changed</h2>
<table>
<tr><th>What happened</th><th>Why it mattered</th><th>What we did</th></tr>
<tr><td>All models together exceed 4 GB</td><td>The card runs out of memory and the demo dies.</td><td>Load one model, free it, then load the next. Stance stays on the small DistilBART checkpoint.</td></tr>
<tr><td>The GPU was not always the device in use</td><td>A CPU run of hundreds of posts is far slower than the 15–25 second GPU budget.</td><td>The review button still caps a live trigger at 50 posts. We do not quote that timing for a full archive or for CPU.</td></tr>
<tr><td>Telegram FloodWait</td><td>A fast loop makes Telegram freeze the account, sometimes for most of an hour.</td><td>One client, a pause between chats, and a sleep for the exact wait Telegram returns. The pull can be stopped and resumed later.</td></tr>
<tr><td>The native Telegram cipher would not build</td><td><code>tgcrypto</code> needs a C compiler this machine did not have.</td><td>Pyrofork fell back to its pure-Python cipher. Collection is slower. It still saves messages.</td></tr>
<tr><td>Two clients, one session file</td><td>The session is SQLite. A second process locks or corrupts it.</td><td>Ingestion is limited to one worker. We do not start a second download while one is open.</td></tr>
<tr><td>Campus Wi-Fi and missing keys</td><td>A review that needs Telegram or a cloud model fails in the room.</td><td>The offline seed is the product. Live Telegram and an online answer model are optional.</td></tr>
<tr><td>Decorative channel titles</td><td>A keyword test on the raw title skipped channels that were in scope.</td><td>Titles are folded to plain letters before the subject check.</td></tr>
<tr><td>A short word matched the wrong title</td><td>A fragment such as “war” inside an unrelated name kept a chat we did not want.</td><td>Blocked words are matched as whole words, and a block list wins unless a title is an explicit keep.</td></tr>
<tr><td>The same audience card appeared three times</td><td>Each analysis run inserted a new snapshot of the same group.</td><td>The page keeps the newest snapshot of each group label.</td></tr>
<tr><td>New downloads did not appear on Sentiment</td><td>That page only shows posts that already have a result, inside 48 hours.</td><td>New rows stay pending until Component B runs. The next run reads the newest message times first. A photo with no words is skipped, because there is no text to label.</td></tr>
<tr><td>Real groups were smaller than 50 accounts</td><td>The privacy rule hides a group under 50. A strict page would look empty.</td><td>The research line stays 50. A demo run may show a smaller card, and the speaker has to say it is below the line.</td></tr>
<tr><td>Ask can sound confident with no evidence</td><td>A language model will invent a theme if it is asked to answer from nothing.</td><td>Search first. If the nearest summary is beyond distance 0.65, Ask stops. The model never sees the raw archive, only the short summaries.</td></tr>
</table>
<h2>6. What we are not claiming</h2>
<table>
<tr><th>Locked choice</th><th>Why a reviewer should hear it</th></tr>
<tr><td>No accuracy percentage</td><td>The comparison benchmarks in Phase 5 have not been run.</td></tr>
<tr><td>No bot or campaign verdict</td><td>The network score is an equal average of three behaviour signals and a screen at 0.70.</td></tr>
<tr><td>No individual profile</td><td>Audience output is a group sketch from public text and posting hour.</td></tr>
<tr><td>No second product inside the dashboard</td><td>There is no PDF export page and no live socket. The page refreshes by ordinary HTTP.</td></tr>
</table>
<div class="say"><strong>One minute.</strong> “Postgres holds the posts. Five agents read them: collection, then one reading per post, then audience, themes, and the graph. The website only calls the API. The exam path is a prepared seed, because Telegram rate limits and a 4 GB graphics card both failed us when we treated the live path as the product.”</div>
""",
)


DOCS["Whole_Project_Plain_Words"] = (
    "The whole project, in plain words",
    "One pass from a saved post to the seven pages, written so any teammate can explain it.",
    """
<div class="note">Read this once before the review. The five agent briefs and the stack brief have the detail. This page is the story you tell if you only get a few minutes.</div>
<h2>1. What we built</h2>
<p>We built a small system that reads public Telegram posts and turns them into a dashboard. It shows how the wording feels, who seems to be speaking as a group, which themes are speeding up, and which accounts sit close together in the conversation. A person can also ask a question, and the answer has to come from those summaries.</p>
<p>It is a student prototype for a second review. It is not a finished intelligence product. It does not watch private chats, and it does not decide that a person is a bot or that a campaign is real.</p>
<h2>2. The idea in one breath</h2>
<p>Save the post. Read the post. Then look across many posts at once. The first step is storage. The second step is one post at a time. The third step is a time window, usually the last 48 hours, using the time Telegram put on the message. The clock on our download does not count, because that clock only measures how late we were.</p>
<div class="figure">
<svg viewBox="0 0 720 118" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="120" height="64" fill="#1f4fff"/>
  <text x="68" y="42" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">1. Save</text>
  <text x="68" y="60" text-anchor="middle" fill="white" font-size="11" font-family="Segoe UI">the post</text>
  <rect x="152" y="16" width="120" height="64" fill="#111"/>
  <text x="212" y="42" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">2. Read</text>
  <text x="212" y="60" text-anchor="middle" fill="#d6ff3f" font-size="11" font-family="Segoe UI">one post</text>
  <rect x="296" y="16" width="200" height="64" fill="#eef2ff" stroke="#1f4fff"/>
  <text x="396" y="38" text-anchor="middle" font-size="13" font-family="Segoe UI">3. Look across</text>
  <text x="396" y="56" text-anchor="middle" font-size="11" font-family="Segoe UI">the last 48 hours</text>
  <text x="396" y="70" text-anchor="middle" font-size="10" font-family="Segoe UI">group, themes, graph</text>
  <rect x="520" y="16" width="184" height="64" fill="#fff" stroke="#111"/>
  <text x="612" y="42" text-anchor="middle" font-size="13" font-family="Segoe UI">4. Ask</text>
  <text x="612" y="60" text-anchor="middle" font-size="11" font-family="Segoe UI">only from summaries</text>
  <path d="M128 48 H152 M272 48 H296 M496 48 H520" stroke="#111" stroke-width="1.5"/>
</svg>
<p class="caption">Figure 1. Four steps. Nothing on the right is allowed to invent a fact that the left-hand steps did not write down.</p>
</div>
<h2>3. The five jobs</h2>
<table>
<tr><th>Job</th><th>Plain meaning</th><th>What you open</th></tr>
<tr><td>Collection</td><td>Put the public post in the database, once. Mark it as waiting.</td><td>Sources</td></tr>
<tr><td>Reading</td><td>Say whether the text is positive, neutral, or negative. Add an emotion, a stance toward the channel topic, and a sarcasm warning. Count the reaction emoji separately.</td><td>Sentiment</td></tr>
<tr><td>Audience</td><td>Sketch the group that spoke in the window: rough interests and the hours they post. Not a file on one person.</td><td>Audience</td></tr>
<tr><td>Themes</td><td>Put similar posts together and see which cluster is arriving faster in the later half of the window.</td><td>Trends</td></tr>
<tr><td>Network</td><td>Draw forwards, replies, and mentions. Colour communities. Flag accounts whose behaviour score averages 0.70 or more.</td><td>Network</td></tr>
</table>
<p>The first page, Overview, is only the counts: how many posts are saved, how many are still waiting, and the latest window. Ask is the last page. It is not a sixth analysis. It searches the short notes the other jobs already wrote.</p>
<h2>4. What happens when someone clicks Run analysis</h2>
<ol>
<li>Take waiting posts that have words. For the review button, stop at 50 so the machine can finish.</li>
<li>Read them one model at a time. The graphics card has 4 GB, so the models cannot all sit in memory together. A photo with no caption is skipped.</li>
<li>Mark those posts as done.</li>
<li>Recompute the audience, the themes, and the graph for the time window.</li>
<li>Write short summaries. Ask can search those summaries afterwards.</li>
</ol>
<p>A post that was just downloaded does not appear on Sentiment until this run has read it. Collection and reading are different steps on purpose. If the network drops, the saved posts are still there.</p>
<div class="figure">
<svg viewBox="0 0 720 78" xmlns="http://www.w3.org/2000/svg">
  <rect x="8" y="16" width="150" height="44" fill="#fff" stroke="#111"/><text x="83" y="43" text-anchor="middle" font-size="13" font-family="Segoe UI">Waiting</text>
  <rect x="186" y="16" width="170" height="44" fill="#1f4fff"/><text x="271" y="43" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Read the words</text>
  <rect x="384" y="16" width="150" height="44" fill="#111"/><text x="459" y="43" text-anchor="middle" fill="white" font-size="13" font-family="Segoe UI">Done</text>
  <rect x="562" y="16" width="146" height="44" fill="#eef2ff" stroke="#1f4fff"/><text x="635" y="43" text-anchor="middle" font-size="13" font-family="Segoe UI">Refresh pages</text>
  <path d="M158 38 H186 M356 38 H384 M534 38 H562" stroke="#111" stroke-width="1.4"/>
</svg>
<p class="caption">Figure 2. The button does not download anything. It only reads posts that are already saved.</p>
</div>
<h2>5. Where a post can come from</h2>
<p>For the review, use the prepared seed. It needs no internet. The same tables can also hold a Telegram Desktop export, or a live read of public channels on our subjects. The live read keeps the latest 80 messages and any photos, and Telegram can pause it for a long wait. That is why the live read is optional. All three sources become the same kind of row. The message time stays the message time.</p>
<h2>6. How a question is answered</h2>
<p>Ask does not browse the raw posts and guess. It turns the question into numbers, finds the nearest short summaries, and stops if even the nearest one is a poor match. Only then does a language model write a paragraph from those summaries. The question and the summaries are stored, so we can show what the answer was based on.</p>
<div class="say"><strong>Say this.</strong> “If the search finds nothing close, we would rather show no answer than a fluent invention.”</div>
<h2>7. A two-minute walkthrough</h2>
<ol>
<li>Open Overview. “These are saved posts and posts still waiting to be read.”</li>
<li>Open Sources. “Collection only stores. It does not judge the text.”</li>
<li>Open Sentiment. “The bars are the wording. The reaction row is people tapping emoji. Sarcasm warns us. It does not flip the label.”</li>
<li>Open Audience. “This is a sketch of the group. If the count is under 50, say it is below our privacy line.”</li>
<li>Open Trends. “This cluster is arriving faster in the second half of the window. The words are extracted, not a headline we wrote.”</li>
<li>Open Network. “Lines are forwards, replies, and mentions. A mark at 0.70 is a screen, not an accusation.”</li>
<li>Open Ask. Ask one prepared question. Point at the passages under the answer.</li>
</ol>
<h2>8. Sentences that stay true</h2>
<table>
<tr><th>If they ask</th><th>Answer</th></tr>
<tr><td>Did you train the models?</td><td>No. We use published models as they are.</td></tr>
<tr><td>How accurate is it?</td><td>We have not run the comparison benchmarks yet, so we are not quoting a percentage.</td></tr>
<tr><td>Is this person a bot?</td><td>No. The number is three ordinary behaviour checks, averaged, with a line at 0.70.</td></tr>
<tr><td>Why is a new channel missing from the charts?</td><td>It is saved and still waiting. The charts show posts that have been read, inside the time window.</td></tr>
<tr><td>What if Telegram is down in the room?</td><td>We replay the prepared seed. The review does not need the live account.</td></tr>
</table>
<div class="say"><strong>Close with this.</strong> “We store public posts, read each one, then summarise the window as a group, a set of themes, and a graph. The pages only display those results, and a question is allowed only when a saved summary is actually close.”</div>
""",
)


def main() -> None:
    HTML.mkdir(parents=True, exist_ok=True)
    for stem, (title, subtitle, body) in DOCS.items():
        path = HTML / f"{stem}.html"
        path.write_text(page(title, subtitle, body), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
