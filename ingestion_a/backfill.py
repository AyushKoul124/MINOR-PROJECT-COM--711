"""Offline backfill and seed replay tool for Component A.

Provides two core offline capabilities required for the demo invariant:
1. --offline: Reset existing seed post timestamps to recent UTC windows
   so downstream components (B/C/D/E) see them as "fresh" data.
2. --generate: Generate additional synthetic posts from templates for
   richer demo datasets without touching Telegram API.

Usage:
    # Replay seed data with recent timestamps (primary demo command)
    python -m ingestion_a.backfill --offline

    # Replay and also generate extra synthetic posts
    python -m ingestion_a.backfill --offline --generate --count 50

    # Dry run (preview SQL without executing)
    python -m ingestion_a.backfill --offline --dry-run
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from storage.database import SyncSessionLocal, sync_engine
from storage.models.raw import IngestionRun, MonitoredChannel, RawPost

logger = logging.getLogger("ingestion_a.backfill")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)


# ─── Synthetic Post Templates ────────────────────────────────────────────────
# Realistic multi-dialectal templates for offline demo generation.
# Each template is a (content_text, content_language, channel_group) tuple.
SYNTHETIC_TEMPLATES: list[tuple[str, str, str]] = [
    # ISRO & Space
    (
        "PSLV-C59 mission successfully deploys EOS-08 earth observation satellite into "
        "sun-synchronous orbit at 535km altitude. All solar panels deployed nominally.",
        "en", "space",
    ),
    (
        "Aditya-L1 spacecraft completes 6 months at L1 Lagrange point. VELC coronagraph "
        "has captured over 16,000 solar corona images with unprecedented resolution.",
        "en", "space",
    ),
    (
        "India ka space sector ab private companies ke liye bhi open ho raha hai. "
        "IN-SPACe ne is quarter 4 new startups ko launch authorization diya! 🚀",
        "hi", "space",
    ),
    (
        "Chandrayaan-4 mission architecture finalized: dual-module lander with sample "
        "return capability. Target launch window Q3 2027 via LVM3-M5.",
        "en", "space",
    ),
    (
        "ISRO-NASA NISAR satellite integration complete at SDSC-SHAR. Joint L-band and "
        "S-band SAR will map entire Earth surface every 12 days.",
        "en", "space",
    ),

    # Defense & DRDO
    (
        "Tejas Mk2 prototype rolls out from HAL Bengaluru facility with GE-F414 engine "
        "integration. First flight expected within 18 months.",
        "en", "defense",
    ),
    (
        "BrahMos-NG (Next Generation) completes third consecutive guided test from INS "
        "Visakhapatnam. Range extended to 450km with weight reduced by 50%.",
        "en", "defense",
    ),
    (
        "Atmanirbhar Bharat defense exports cross $3.5B mark this fiscal year. Major "
        "contracts include BrahMos, Akash SAM, and Dornier Do-228 aircraft.",
        "en", "defense",
    ),
    (
        "DRDO ka naya MPATGM anti-tank missile system successfully tested. Infantry "
        "troops ke liye game-changer hai ye man-portable system! 🎯",
        "hi", "defense",
    ),
    (
        "Fifth-gen AMCA stealth fighter program receives Cabinet Committee on Security "
        "approval. ₹15,000 crore sanctioned for five prototype aircraft.",
        "en", "defense",
    ),

    # Geopolitics & Strategy
    (
        "India-France defence cooperation reaches new milestone: joint development MoU "
        "for submarine-launched cruise missile technology transfer framework.",
        "en", "geopolitics",
    ),
    (
        "Maritime Domain Awareness partnership between India and Japan expanded to cover "
        "entire Indo-Pacific region via shared satellite AIS data feeds.",
        "en", "geopolitics",
    ),
    (
        "China ke J-20 stealth fighters LAC ke paas dekhe gaye hain. IAF ne respond "
        "karte hue Rafale squadron ko forward base par deploy kiya hai.",
        "hi", "geopolitics",
    ),
    (
        "Quad nations announce joint cybersecurity framework for critical undersea cable "
        "infrastructure protection across Indo-Pacific sea lanes.",
        "en", "geopolitics",
    ),

    # Science & Tech Policy
    (
        "National Quantum Mission achieves major breakthrough: IISc team demonstrates "
        "8-qubit photonic quantum processor with 99.2% gate fidelity.",
        "en", "tech",
    ),
    (
        "India Semiconductor Mission approves second fabrication unit in Gujarat. "
        "Tower Semiconductor JV to produce 65nm chips for IoT and automotive.",
        "en", "tech",
    ),
    (
        "Bharat 6G Alliance releases first technical standards draft. Indigenous 6G "
        "testbed at IIT Madras achieves 1Tbps throughput in lab conditions.",
        "en", "tech",
    ),
    (
        "Semiconductor plant mein kaam tezi se chal raha hai. 2027 tak India ke paas "
        "khud ke chips honge — defense aur space dono ke liye critical hai! 💡",
        "hi", "tech",
    ),
    (
        "CERT-In issues advisory on critical vulnerability in SCADA systems used in "
        "power grid infrastructure. All utilities directed to patch within 72 hours.",
        "en", "tech",
    ),

    # CIB-style near-duplicate pair (for testing Coordinated Inauthentic Behavior detection)
    (
        "BREAKING: Indigenous nuclear submarine INS Arighat achieves initial operational "
        "clearance. India now has credible sea-based nuclear deterrent capability.",
        "en", "defense",
    ),
]

# Map topic groups to channel identifiers from channels.yaml
CHANNEL_GROUP_MAP: dict[str, list[str]] = {
    "space": [
        "@isro_updates", "@indianspace_discussion", "@isrospaceupdates",
        "@indianspaceresearch", "@gaganyaan_mission", "@space_india_portal",
    ],
    "defense": [
        "@drdo_updates", "@indiandefenceupdate", "@defencenewsindia",
        "@aerospace_defence_india", "@idrw_org", "@bharat_defence",
    ],
    "geopolitics": [
        "@strategic_affairs_in", "@geopolitics_india", "@indiadiplomacy",
        "@southasiandefence", "@stratfront", "@indiastrategic",
    ],
    "tech": [
        "@csir_india", "@indiatechpolicy", "@vigyanprasar",
        "@digital_india_news", "@meity_updates", "@quantum_mission_india",
    ],
}

# Author IDs from seed data
SEED_AUTHOR_IDS = [
    "user_101", "user_102", "user_103", "user_104",
    "user_105", "user_106", "user_107", "user_108",
    None,  # Channel broadcast (no author)
]


def _reset_timestamps_to_recent(session, hours_window: int = 72) -> int:
    """Reset all existing raw_posts.posted_at to recent UTC timestamps.

    Distributes posts uniformly across the last `hours_window` hours so
    they appear as freshly ingested data for downstream components.

    Returns:
        Number of posts updated.
    """
    # Get all existing posts ordered by original posted_at
    result = session.execute(
        text("SELECT id FROM raw_posts ORDER BY posted_at ASC")
    )
    post_ids = [row[0] for row in result.fetchall()]

    if not post_ids:
        logger.info("No existing posts to reset.")
        return 0

    now = datetime.now(timezone.utc)
    total = len(post_ids)
    interval = timedelta(hours=hours_window) / total

    for idx, post_id in enumerate(post_ids):
        new_timestamp = now - timedelta(hours=hours_window) + (interval * idx)
        session.execute(
            update(RawPost)
            .where(RawPost.id == post_id)
            .values(
                posted_at=new_timestamp,
                ingested_at=new_timestamp + timedelta(seconds=random.randint(1, 30)),
                processing_status="pending",  # Reset to pending for re-processing
            )
        )

    session.commit()
    logger.info(
        "Reset %d posts to recent timestamps (last %d hours).",
        total,
        hours_window,
    )
    return total


def _generate_synthetic_posts(
    session,
    count: int = 20,
    hours_window: int = 48,
) -> int:
    """Generate additional synthetic posts from templates.

    Distributes posts across channels matching their topic group,
    with timestamps spread over the last `hours_window` hours.

    Returns:
        Number of posts generated.
    """
    # Create a new ingestion run for synthetic data
    run_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    session.execute(
        pg_insert(IngestionRun).values(
            id=run_id,
            started_at=now,
            completed_at=now,
            platform="telegram",
            channel_ids=["synthetic_backfill"],
            posts_collected=0,
            status="running",
        )
    )

    generated = 0
    for i in range(count):
        template = SYNTHETIC_TEMPLATES[i % len(SYNTHETIC_TEMPLATES)]
        content_text, lang, group = template
        channel = random.choice(CHANNEL_GROUP_MAP.get(group, ["@isro_updates"]))
        author = random.choice(SEED_AUTHOR_IDS)

        # Spread timestamps uniformly across the window
        post_time = now - timedelta(
            hours=hours_window * (1 - i / count),
            minutes=random.randint(0, 59),
            seconds=random.randint(0, 59),
        )

        post_id = f"synth_{run_id.hex[:8]}_{i:04d}"

        # Use INSERT ... ON CONFLICT to avoid duplicates on re-run
        stmt = pg_insert(RawPost).values(
            platform="telegram",
            platform_post_id=post_id,
            channel_id=channel,
            author_id=author,
            content_text=content_text,
            content_language=lang,
            view_count=random.randint(500, 20000),
            reaction_counts={
                random.choice(["👍", "🚀", "🔥", "💡", "🎯"]): random.randint(50, 500),
                random.choice(["❤️", "👏", "💪", "🇮🇳"]): random.randint(20, 300),
            },
            ingested_at=post_time + timedelta(seconds=random.randint(1, 60)),
            posted_at=post_time,
            ingestion_run_id=run_id,
            processing_status="pending",
        ).on_conflict_do_nothing(
            constraint="uq_raw_posts_platform_post_id"
        )

        session.execute(stmt)
        generated += 1

    # Update ingestion run with final count
    session.execute(
        update(IngestionRun)
        .where(IngestionRun.id == run_id)
        .values(posts_collected=generated, status="completed", completed_at=now)
    )

    session.commit()
    logger.info("Generated %d synthetic posts across channels.", generated)
    return generated


def _verify_channels_exist(session) -> int:
    """Verify monitored_channels table is seeded. Returns count."""
    result = session.execute(text("SELECT COUNT(*) FROM monitored_channels"))
    count = result.scalar()
    if count == 0:
        logger.warning(
            "No channels in monitored_channels table. "
            "Run: scripts/seed_demo_data.sql first."
        )
    else:
        logger.info("Verified %d monitored channels in database.", count)
    return count


def main() -> None:
    """CLI entry point for offline backfill operations."""
    parser = argparse.ArgumentParser(
        prog="backfill",
        description="SOCMINT offline backfill: replay seed data and generate synthetic posts.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Reset existing seed post timestamps to recent UTC windows for demo replay.",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate additional synthetic posts from templates.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=20,
        help="Number of synthetic posts to generate (default: 20).",
    )
    parser.add_argument(
        "--hours",
        type=int,
        default=72,
        help="Time window in hours to spread posts over (default: 72).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without executing database changes.",
    )

    args = parser.parse_args()

    if not args.offline and not args.generate:
        parser.print_help()
        print("\n⚠️  Specify --offline and/or --generate to run backfill operations.")
        sys.exit(1)

    session = SyncSessionLocal()

    try:
        # Verify prerequisites
        channel_count = _verify_channels_exist(session)
        if channel_count == 0:
            logger.error("Aborting: no channels found. Seed the database first.")
            sys.exit(1)

        if args.dry_run:
            logger.info("DRY RUN: No database changes will be made.")
            if args.offline:
                result = session.execute(text("SELECT COUNT(*) FROM raw_posts"))
                logger.info("Would reset %d posts to recent timestamps.", result.scalar())
            if args.generate:
                logger.info("Would generate %d synthetic posts.", args.count)
            return

        total_processed = 0

        if args.offline:
            logger.info("═" * 60)
            logger.info("OFFLINE REPLAY: Resetting timestamps to recent UTC windows")
            logger.info("═" * 60)
            total_processed += _reset_timestamps_to_recent(session, args.hours)

        if args.generate:
            logger.info("═" * 60)
            logger.info("SYNTHETIC GENERATION: Creating %d additional posts", args.count)
            logger.info("═" * 60)
            total_processed += _generate_synthetic_posts(session, args.count, args.hours)

        logger.info("═" * 60)
        logger.info("BACKFILL COMPLETE: %d total posts processed.", total_processed)
        logger.info("═" * 60)

    except Exception as exc:
        logger.error("Backfill failed: %s", exc, exc_info=True)
        session.rollback()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
