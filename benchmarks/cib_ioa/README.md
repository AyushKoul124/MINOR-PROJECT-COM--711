# Offline coordination benchmark

This folder scores Component E against a labelled tweet file. It does not read Telegram, Postgres, or the dashboard.

## Provenance

The file on disk is `all_tweets_hashed.csv` in the project root. It is the Kaggle dataset `pookiewiggington/twitter-information-operations-classification`: confirmed Russian IRA-linked accounts, originally disclosed through Twitter's Information Operations archive, combined with a separately built organic control set. `info_op` 1 is coordinated. `info_op` 0 is organic.

This is not Twitter's raw official archive. Official releases list confirmed coordinated accounts only. The organic rows are a control set packaged with them by the dataset author.

`all_users_hashed.csv` is the same table rolled up to one row per account. It has no individual tweet time, so the synchrony check uses the tweet file.

The tweet file is about 7.4 GB and is listed in `.gitignore`. It is not committed.

## What was scored

The script is `evaluate.py`. One pass keeps a fixed sample:

- seed 42
- 400 accounts from each class
- at most 25 tweets from each kept account

The file contains 22,873,094 tweet rows, 4,427 organic accounts, and 4,167 coordinated accounts. Coordinated rows are interleaved, so tweets are accumulated by `userid` rather than by consecutive blocks. Kept accounts had 25.0 tweets on average in the organic sample and 22.92 in the coordinated sample.

| Signal | Rule |
| --- | --- |
| `posting_synchrony_signal` | Fraction of an account's kept tweets that fall within 120 seconds of a different account in the sample |
| `duplicate_content_signal` | TF-IDF cosine, unigrams and bigrams, 500 features. Half the fraction of tweets whose nearest other-account tweet is at least 0.75, half the mean of those nearest similarities |
| Reported score | Mean of those two signals. A score of 0.70 or above is the positive call |

`age_volume_signal` was excluded from this benchmark evaluation due to the absence of account creation dates in the dataset.

## Result at the live cutoff

| Check | Precision | Recall | F1 | True positive | False positive |
| --- | --- | --- | --- | --- | --- |
| Mean of the two signals | 1.00 | 0.04 | 0.0769 | 16 | 0 |
| Synchrony alone | 1.00 | 0.0475 | 0.0907 | 19 | 0 |
| Duplicate content alone | 0.8019 | 0.2125 | 0.3360 | 85 | 21 |

Each class in the sample has 400 accounts. At 0.70 the two-signal mean missed 384 coordinated accounts and flagged no organic account.

Selected points on the same two-signal curve:

| Threshold | Precision | Recall | F1 |
| --- | --- | --- | --- |
| 0.45 | 0.7945 | 0.29 | 0.4249 |
| 0.50 | 0.9388 | 0.23 | 0.3695 |
| 0.60 | 0.9714 | 0.085 | 0.1563 |
| 0.70 | 1.00 | 0.04 | 0.0769 |

The full curve from 0.00 to 1.00 is in `results.json`. A threshold of 0.00 flags every account, so its F1 is only the balanced-class baseline.

## How to read it

The live pipeline still averages three signals and still flags at 0.70. This file checks the two signals the table can support. The source is a Twitter collection about a Russian operation. The prototype reads public Telegram. Published work has tested synchrony and near-duplicate text across more than one country and platform, which is why the check is still useful, and why the numbers stay indicative rather than a claim about the Telegram demo.

Run it again with:

```powershell
.\.venv\Scripts\python.exe benchmarks\cib_ioa\evaluate.py
```

The pass reads the whole tweet file once. On the reference machine that took about eight minutes.
