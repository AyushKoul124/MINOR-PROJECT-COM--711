-- Post-Viva PII Disposal Routine (ARCHITECTURE §6.3)
-- Run once after the December 2026 viva to wipe personal text from the dev database.
-- Usage: psql -U socmint -d socmint -f scripts/post_viva_scrub.sql

BEGIN;

-- 1. Wipe raw message content and media attachments
UPDATE raw_posts
SET content_text = NULL,
    media_urls = NULL;

-- 2. Wipe author personal identifiers
UPDATE raw_authors
SET display_name = NULL,
    bio_text = NULL;

COMMIT;
