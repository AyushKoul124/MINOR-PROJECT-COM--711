"""Component A: Ingestion Agent for public Telegram channels and offline seed replay.

Submodules:
    adapters/        Platform-specific message fetchers (Telegram MTProto via Pyrofork)
    backfill.py      Offline demo replay & synthetic post generation
    import_exported.py  Telegram Desktop JSON export importer
    tasks.py         Celery task definitions for live staggered polling
"""
