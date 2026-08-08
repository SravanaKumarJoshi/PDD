-- Migration: Add updated_at column to filtered_polymers for delta-sync support
-- Run once against your MySQL instance.
-- Safe to re-run: uses IF NOT EXISTS / column check pattern.

-- Step 1: Add the column (only if it doesn't already exist)
ALTER TABLE filtered_polymers
    ADD COLUMN IF NOT EXISTS updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP;

-- Step 2: Back-fill existing rows so they are returned on the first full sync.
-- Setting to epoch means the Android client's first sync (since=1970-...) will
-- correctly include all rows.
UPDATE filtered_polymers
SET updated_at = '1970-01-01 00:00:01'
WHERE updated_at = '1970-01-01 00:00:00' OR updated_at IS NULL;

-- Step 3: Add index so the sync query (WHERE updated_at > ?) uses a range scan.
CREATE INDEX IF NOT EXISTS idx_filtered_polymers_updated_at
    ON filtered_polymers (updated_at);
