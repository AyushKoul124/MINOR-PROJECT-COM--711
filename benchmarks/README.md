# Benchmarks

`cib_ioa/` is the offline precision, recall, and F1 check for Component E.

The source file is `all_tweets_hashed.csv` in the project root (Kaggle `pookiewiggington/twitter-information-operations-classification`). It is not Twitter's raw official archive. It combines confirmed Russian IRA-linked accounts with a separately built organic control set, labelled by `info_op`.

The score uses posting synchrony and duplicate content. `age_volume_signal` was excluded because the file has no account-creation date. The measured figures, the sample, and the Twitter-to-Telegram caveat are in `cib_ioa/README.md` and `cib_ioa/results.json`.
