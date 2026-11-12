"""Offline precision, recall, and F1 for two Component E signals.

The live pipeline is not involved. This script reads the local hashed tweet
file (``all_tweets_hashed.csv``), which is the Kaggle information-operations
table: ``info_op`` 1 is a coordinated account, 0 is organic.

``age_volume_signal`` is not scored. The file has no account-creation date.

The full table is about 22 million rows, and the coordinated rows are not
stored as one block per account. A full TF-IDF pass does not fit the reference
machine, so the script keeps a fixed random sample:

- 400 accounts from each class (seed 42), chosen by userid across the file
- at most 25 tweets from each kept account

Synchrony is the same rule as ``network_e.cib_signals.py``: the fraction of an
account's kept tweets that fall within 120 seconds of a tweet by a different
account in the sample. Duplicate content is the same mix of TF-IDF cosine
figures: half the fraction of tweets whose nearest other-account tweet is at
least 0.75, half the average of those nearest similarities.

The reported score is the mean of those two signals. A score of 0.70 or above
is the positive prediction. That is the live cutoff applied to the two signals
this file can support.
"""

from __future__ import annotations

import ast
import csv
import json
import random
import sys
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parents[2]
TWEET_PATH = ROOT / "all_tweets_hashed.csv"
OUT_PATH = Path(__file__).resolve().parent / "results.json"

SEED = 42
USERS_PER_CLASS = 400
TWEETS_PER_USER = 25
SYNCHRONY_SECONDS = 120.0
DUP_SIM_CUTOFF = 0.75
FLAG_THRESHOLD = 0.70
MIN_TOKENS = 4


@dataclass
class Account:
    label: int
    times: list[float] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)


def _text_from_bow(raw: str) -> str:
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("["):
        try:
            parsed = ast.literal_eval(raw)
        except (SyntaxError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            raw = " ".join(str(token) for token in parsed if token)
    if len(raw.split()) < MIN_TOKENS:
        return ""
    return raw


def _remember_tweet(pack: Account, seen: int, when: float, text: str) -> int:
    """Keep a fixed random subset of one account's tweets."""
    seen += 1
    if len(pack.times) < TWEETS_PER_USER:
        pack.times.append(when)
        pack.texts.append(text)
        return seen
    slot = random.randrange(seen)
    if slot < TWEETS_PER_USER:
        pack.times[slot] = when
        pack.texts[slot] = text
    return seen


def _consider_account(
    pools: dict[int, dict[str, Account]],
    seen_accounts: dict[int, int],
    userid: str,
    pack: Account,
) -> None:
    label = pack.label
    seen_accounts[label] = seen_accounts.get(label, 0) + 1
    pool = pools[label]
    if len(pool) < USERS_PER_CLASS:
        pool[userid] = pack
        return
    if random.randrange(seen_accounts[label]) < USERS_PER_CLASS:
        drop = random.choice(tuple(pool))
        del pool[drop]
        pool[userid] = pack


def load_sample(path: Path) -> tuple[dict[str, Account], dict[int, int]]:
    """One pass. Coordinated rows are interleaved, so tweets accumulate by userid."""
    csv.field_size_limit(sys.maxsize)
    random.seed(SEED)
    pools: dict[int, dict[str, Account]] = {0: {}, 1: {}}
    seen_accounts: dict[int, int] = {0: 0, 1: 0}
    seen_ids: set[str] = set()
    tweet_seen: dict[str, int] = {}
    rows = 0

    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        time_at = header.index("tweet_time")
        user_at = header.index("userid")
        bow_at = header.index("BoW")
        label_at = header.index("info_op")

        for row in reader:
            rows += 1
            if rows % 1_000_000 == 0:
                print(
                    f"rows {rows} kept {len(pools[0])}+{len(pools[1])} "
                    f"seen_accounts {seen_accounts.get(0, 0)}+{seen_accounts.get(1, 0)}",
                    flush=True,
                )
            userid = row[user_at]
            if userid not in seen_ids:
                try:
                    label = int(float(row[label_at]))
                except ValueError:
                    continue
                if label not in (0, 1):
                    continue
                seen_ids.add(userid)
                _consider_account(pools, seen_accounts, userid, Account(label=label))
            pack = pools[0].get(userid) or pools[1].get(userid)
            if pack is None:
                continue
            try:
                when = datetime.fromisoformat(row[time_at]).timestamp()
            except ValueError:
                continue
            tweet_seen[userid] = _remember_tweet(
                pack, tweet_seen.get(userid, 0), when, row[bow_at]
            )

    kept = {**pools[0], **pools[1]}
    for pack in kept.values():
        pack.texts = [_text_from_bow(raw) for raw in pack.texts]
    print(
        f"scan_done rows {rows} organic {len(pools[0])} coordinated {len(pools[1])} "
        f"accounts_seen {seen_accounts.get(0, 0)}+{seen_accounts.get(1, 0)}",
        flush=True,
    )
    return kept, seen_accounts


def synchrony_scores(accounts: dict[str, Account]) -> dict[str, float]:
    events: list[tuple[float, str]] = []
    for userid, pack in accounts.items():
        events.extend((when, userid) for when in pack.times)
    events.sort()
    stamps = [when for when, _userid in events]
    scores: dict[str, float] = {}
    for userid, pack in accounts.items():
        if not pack.times:
            scores[userid] = 0.0
            continue
        hits = 0
        for when in pack.times:
            left = bisect_left(stamps, when - SYNCHRONY_SECONDS)
            right = bisect_right(stamps, when + SYNCHRONY_SECONDS)
            if any(events[index][1] != userid for index in range(left, right)):
                hits += 1
        scores[userid] = round(hits / len(pack.times), 4)
    return scores


def duplicate_scores(accounts: dict[str, Account]) -> dict[str, float]:
    owners: list[str] = []
    corpus: list[str] = []
    for userid, pack in accounts.items():
        for text in pack.texts:
            if text:
                owners.append(userid)
                corpus.append(text)
    if not corpus:
        return {userid: 0.0 for userid in accounts}

    matrix = TfidfVectorizer(
        stop_words="english",
        ngram_range=(1, 2),
        max_features=500,
    ).fit_transform(corpus)
    by_owner: dict[str, list[int]] = defaultdict(list)
    for index, userid in enumerate(owners):
        by_owner[userid].append(index)

    scores: dict[str, float] = {}
    for userid in accounts:
        own = by_owner.get(userid, [])
        if not own:
            scores[userid] = 0.0
            continue
        other = [index for index, owner in enumerate(owners) if owner != userid]
        if not other:
            scores[userid] = 0.0
            continue
        nearest = cosine_similarity(matrix[own], matrix[other]).max(axis=1)
        high = float(sum(1 for value in nearest if value >= DUP_SIM_CUTOFF) / len(nearest))
        scores[userid] = round(min(1.0, 0.5 * high + 0.5 * float(nearest.mean())), 4)
    return scores


def _binary_counts(y_true: list[int], y_pred: list[int]) -> dict[str, float]:
    precision, recall, f1, _support = precision_recall_fscore_support(
        y_true,
        y_pred,
        average="binary",
        pos_label=1,
        zero_division=0,
    )
    matrix = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "true_negative": int(matrix[0, 0]),
        "false_positive": int(matrix[0, 1]),
        "false_negative": int(matrix[1, 0]),
        "true_positive": int(matrix[1, 1]),
    }


def evaluate(accounts: dict[str, Account]) -> dict:
    sync = synchrony_scores(accounts)
    dup = duplicate_scores(accounts)
    rows = []
    for userid, pack in accounts.items():
        s1 = sync[userid]
        s3 = dup[userid]
        score = round((s1 + s3) / 2.0, 4)
        rows.append({
            "userid": userid,
            "info_op": pack.label,
            "posting_synchrony_signal": s1,
            "duplicate_content_signal": s3,
            "score": score,
        })

    y_true = [row["info_op"] for row in rows]
    curve = []
    for step in range(0, 21):
        cutoff = round(step / 20.0, 2)
        predicted = [1 if row["score"] >= cutoff else 0 for row in rows]
        point = _binary_counts(y_true, predicted)
        point["threshold"] = cutoff
        curve.append(point)

    at_default = next(point for point in curve if point["threshold"] == FLAG_THRESHOLD)
    sync_pred = [1 if row["posting_synchrony_signal"] >= FLAG_THRESHOLD else 0 for row in rows]
    dup_pred = [1 if row["duplicate_content_signal"] >= FLAG_THRESHOLD else 0 for row in rows]
    return {
        "dataset": str(TWEET_PATH.name),
        "seed": SEED,
        "users_per_class_cap": USERS_PER_CLASS,
        "tweets_per_user_cap": TWEETS_PER_USER,
        "accounts": len(rows),
        "organic": sum(1 for row in rows if row["info_op"] == 0),
        "coordinated": sum(1 for row in rows if row["info_op"] == 1),
        "mean_tweets_organic": round(
            sum(len(pack.times) for pack in accounts.values() if pack.label == 0)
            / max(1, sum(1 for pack in accounts.values() if pack.label == 0)),
            2,
        ),
        "mean_tweets_coordinated": round(
            sum(len(pack.times) for pack in accounts.values() if pack.label == 1)
            / max(1, sum(1 for pack in accounts.values() if pack.label == 1)),
            2,
        ),
        "signals": ["posting_synchrony_signal", "duplicate_content_signal"],
        "excluded_signal": "age_volume_signal",
        "excluded_reason": "The file has no account creation date.",
        "score": "(posting_synchrony_signal + duplicate_content_signal) / 2",
        "flag_threshold": FLAG_THRESHOLD,
        "synchrony_window_seconds": SYNCHRONY_SECONDS,
        "duplicate_similarity_cutoff": DUP_SIM_CUTOFF,
        "at_0_70": at_default,
        "synchrony_only_at_0_70": _binary_counts(y_true, sync_pred),
        "duplicate_only_at_0_70": _binary_counts(y_true, dup_pred),
        "threshold_curve": curve,
    }


def main() -> None:
    if not TWEET_PATH.is_file():
        raise SystemExit(f"Missing tweet file: {TWEET_PATH}")
    print(f"reading {TWEET_PATH.name}", flush=True)
    accounts, seen_accounts = load_sample(TWEET_PATH)
    if not accounts:
        raise SystemExit("No accounts were kept.")
    print("scoring", flush=True)
    report = evaluate(accounts)
    report["accounts_seen"] = {
        "organic": seen_accounts.get(0, 0),
        "coordinated": seen_accounts.get(1, 0),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    headline = report["at_0_70"]
    print(
        f"threshold {FLAG_THRESHOLD} precision {headline['precision']} "
        f"recall {headline['recall']} f1 {headline['f1']}",
        flush=True,
    )
    print(f"wrote {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
