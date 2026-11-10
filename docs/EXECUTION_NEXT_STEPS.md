# Execution next steps (after "go for it")

## Blocker

Implementation requires **Agent mode**. Plan mode allows only markdown edits; `.py` / `.jsx` / `.css` changes were rejected.

**Action:** In Cursor, switch this chat to **Agent** (not Plan), then send:

```text
Execute the full upgrade plan: Wave 1–4 backend (RAG after trigger, auth, gitignore, post_viva_scrub) + frontend visual refresh per docs/FRONTEND_UPGRADE_SPEC.md
```

## Priority backend (Wave 3)

1. **`orchestrator/coordinator.py`** — After window C/D/E in `trigger_full_analysis`, call `RAGIndexer().index_all_components()`; add `rag_indexing` to telemetry dict.
2. **`api/auth.py`** — HTTP Basic Auth using `API_BASIC_AUTH_USERNAME` / `API_BASIC_AUTH_PASSWORD` from `.env`; skip if password empty (dev).
3. **`.gitignore`** — Add `Telegram Desktop/`
4. **`scripts/post_viva_scrub.sql`** — ARCHITECTURE §6.3 PII wipe

## Priority frontend

See [FRONTEND_UPGRADE_SPEC.md](./FRONTEND_UPGRADE_SPEC.md) — mesh canvas, agent letter pills, cyan primary `#0ea5e9`, pipeline strip, softer viva copy (academic testbed, not "NTRO product").
