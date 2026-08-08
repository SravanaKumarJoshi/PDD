-- =============================================================================
-- Migration: Add updated_at column and index to filtered_polymers
--
-- Purpose
-- -------
-- The streaming delta-sync endpoint (GET /api/v1/materials/stream) filters
-- rows with:
--
--     WHERE updated_at > :since ORDER BY updated_at ASC, polymer ASC
--
-- Without an index on updated_at, MySQL performs a full table scan on every
-- sync request.  With 100 K+ rows this causes the Android client to hit its
-- 30-second read timeout on every incremental sync, even though only a
-- handful of rows changed.
--
-- This migration:
--   1. Adds the updated_at column to filtered_polymers (if missing).
--   2. Back-fills existing rows to the current timestamp.
--   3. Creates a composite index on (updated_at, polymer) to cover the
--      ORDER BY clause without a filesort.
--   4. Adds an is_deleted column (soft-delete support).
--   5. Creates a separate index on is_deleted for the cleanup queries.
--
-- Idempotency
-- -----------
-- All statements use IF NOT EXISTS / IF EXISTS so the migration is safe to
-- re-run.  Check the information_schema queries at the bottom to verify the
-- migration was applied.
--
-- Execution
-- ---------
--   mysql -u <user> -p <database> < add_updated_at_index.sql
--
-- Or via Python:
--   from app.database import engine
--   with engine.connect() as conn:
--       conn.execute(text(open("scripts/migrations/add_updated_at_index.sql").read()))
--
-- Rollback
-- --------
--   ALTER TABLE filtered_polymers DROP INDEX idx_fp_updated_at_polymer;
--   ALTER TABLE filtered_polymers DROP INDEX idx_fp_is_deleted;
--   ALTER TABLE filtered_polymers DROP COLUMN updated_at;
--   ALTER TABLE filtered_polymers DROP COLUMN is_deleted;
-- =============================================================================

-- ─── 1. Add updated_at column ────────────────────────────────────────────────
-- The DATETIME(6) type gives microsecond precision, matching Python's
-- datetime.now(timezone.utc) which also has microsecond resolution.
-- DEFAULT CURRENT_TIMESTAMP(6) ensures new rows are automatically timestamped.
-- ON UPDATE CURRENT_TIMESTAMP(6) ensures the column is bumped on every UPDATE.

SET @col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'filtered_polymers'
      AND COLUMN_NAME  = 'updated_at'
);

SET @add_updated_at = IF(
    @col_exists = 0,
    'ALTER TABLE filtered_polymers
         ADD COLUMN updated_at DATETIME(6) NOT NULL
         DEFAULT CURRENT_TIMESTAMP(6)
         ON UPDATE CURRENT_TIMESTAMP(6)
         COMMENT ''Row last-modified timestamp used by delta-sync''',
    'SELECT ''updated_at column already exists — skipping'' AS info'
);

PREPARE stmt FROM @add_updated_at;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;


-- ─── 2. Back-fill existing rows ───────────────────────────────────────────────
-- Rows inserted before the migration have updated_at = DEFAULT (the migration
-- time).  This is intentional: the first client sync after the migration runs
-- as a full-catalog sync (since=epoch → all rows are "after" epoch) so every
-- existing row is delivered once regardless of its updated_at value.
--
-- No explicit back-fill is needed because the DEFAULT CURRENT_TIMESTAMP(6)
-- already stamps every existing row with the current time when the ALTER TABLE
-- runs.


-- ─── 3. Composite index: (updated_at, polymer) ───────────────────────────────
-- Covers:  WHERE updated_at > :since ORDER BY updated_at ASC, polymer ASC
-- The ORDER BY is fully resolved by the index — no filesort.
-- LIMIT/OFFSET cursor pagination is O(offset) in MySQL, but that is
-- acceptable for the batch sizes (100-500) used by the sync endpoint.

CREATE INDEX idx_fp_updated_at_polymer
ON filtered_polymers (updated_at, polymer);


-- ─── 4. Add is_deleted column (soft-delete support) ──────────────────────────
SET @del_col_exists = (
    SELECT COUNT(*)
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME   = 'filtered_polymers'
      AND COLUMN_NAME  = 'is_deleted'
);

SET @add_is_deleted = IF(
    @del_col_exists = 0,
    'ALTER TABLE filtered_polymers
         ADD COLUMN is_deleted TINYINT(1) NOT NULL DEFAULT 0
         COMMENT ''1 = soft-deleted; included in sync so clients can purge locally''',
    'SELECT ''is_deleted column already exists — skipping'' AS info'
);

PREPARE stmt2 FROM @add_is_deleted;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;


-- ─── 5. Index on is_deleted ───────────────────────────────────────────────────
-- Used by admin cleanup queries: SELECT * FROM filtered_polymers WHERE is_deleted = 1
-- A partial index would be ideal but MySQL does not support partial indexes;
-- a full index on a TINYINT column is negligible in size.

CREATE INDEX idx_fp_is_deleted
ON filtered_polymers (is_deleted);


-- ─── Verification queries ─────────────────────────────────────────────────────
-- Run these after the migration to confirm everything was applied correctly.

SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_DEFAULT,
    EXTRA
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'filtered_polymers'
  AND COLUMN_NAME IN ('updated_at', 'is_deleted')
ORDER BY COLUMN_NAME;

SELECT
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) AS columns,
    NON_UNIQUE
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'filtered_polymers'
  AND INDEX_NAME IN ('idx_fp_updated_at_polymer', 'idx_fp_is_deleted')
GROUP BY INDEX_NAME, NON_UNIQUE;
