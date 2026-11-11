# Execution next steps (after "go for it")

## Status

Waves 1–4 applied in Agent mode (see `UPGRADE_STATUS.md`). Wave 5 (benchmarks + offline rehearsal) remains manual verification on reference hardware.

## Priority backend (Wave 3)

1. **`orchestrator/coordinator.py`** — After window C/D/E in `trigger_full_analysis`, call `RAGIndexer().index_all_components()`; add `rag_indexing` to telemetry dict.
2. **`api/auth.py`** — HTTP Basic Auth using `API_BASIC_AUTH_USERNAME` / `API_BASIC_AUTH_PASSWORD` from `.env`; skip if password empty (dev).
3. **`.gitignore`** — Add `Telegram Desktop/`
4. **`scripts/post_viva_scrub.sql`** — ARCHITECTURE §6.3 PII wipe

## Priority frontend

See [FRONTEND_UPGRADE_SPEC.md](./FRONTEND_UPGRADE_SPEC.md) — mesh canvas, agent letter pills, cyan primary `#0ea5e9`, pipeline strip, softer viva copy (academic testbed, not "NTRO product").
