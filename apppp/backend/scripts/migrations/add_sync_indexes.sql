-- =============================================================================
-- Migration: add_sync_indexes.sql
-- Comprehensive index set for the streaming SSE sync endpoint.
--
-- Why these indexes?
-- ------------------
-- The streaming endpoint (GET /api/v1/materials/stream) uses keyset pagination:
--
--   Page 1 (first batch after :since):
--     WHERE updated_at > :since
--     ORDER BY updated_at ASC, polymer ASC
--     LIMIT :batch_size
--
--   Page N+1 (keyset resume — O(log N) seek):
--     WHERE updated_at > :since
--       AND (updated_at > :last_ts
--            OR (updated_at = :last_ts AND polymer > :last_poly))
--     ORDER BY updated_at ASC, polymer ASC
--     LIMIT :batch_size
--
--   Count query (run once per stream):
--     SELECT COUNT(*) FROM filtered_polymers WHERE updated_at > :since
--
-- Without idx_fp_updated_at_polymer MySQL performs a full table scan for
-- every batch query.  With 100 K+ rows and batch_size=150 that means 667
-- full scans per sync — each taking 1-30 seconds depending on buffer pool
-- state — causing the Android client to hit its read timeout.
--
-- Indexes added
-- -------------
-- 1. idx_fp_updated_at_polymer  (updated_at, polymer)
--    Covers: WHERE updated_at > ?  ORDER BY updated_at ASC, polymer ASC
--    + keyset condition: updated_at = :last_ts AND polymer > :last_poly
--    This is the PRIMARY performance index.  Every sync query is an
--    O(log N) seek with this index in place.
--
-- 2. idx_fp_category_polymer  (category, polymer)
--    Covers: GET /api/v1/materials?category=... ORDER BY polymer
--    Without this, category filters do a full scan then filesort.
--
-- 3. idx_fp_polymer  (polymer)
--    Covers: GET /api/v1/materials/{id}  WHERE polymer = :id
--    The unique key uq_polymer already covers this; this entry documents
--    that the unique key doubles as the lookup index.
--
-- 4. idx_fp_is_deleted  (is_deleted)
--    Covers: admin cleanup queries WHERE is_deleted = 1.
--
-- Idempotency
-- -----------
-- Uses DROP INDEX IF EXISTS before CREATE INDEX to make re-runs safe.
-- MySQL 8.0+: CREATE INDEX IF NOT EXISTS is not supported, so we use
-- the DROP + CREATE pattern instead.  The brief index absence during
-- re-migration is acceptable in a maintenance window.
--
-- Execution
-- ---------
--   mysql -u <user> -p <database> < scripts/migrations/add_sync_indexes.sql
--
-- Rollback
-- --------
--   DROP INDEX idx_fp_updated_at_polymer ON filtered_polymers;
--   DROP INDEX idx_fp_category_polymer ON filtered_polymers;
--   DROP INDEX idx_fp_is_deleted ON filtered_polymers;
-- =============================================================================

SET NAMES utf8mb4;

-- ─── 0. Prerequisite: updated_at column ──────────────────────────────────────
-- This migration assumes the updated_at column already exists.
-- If it does not, run add_updated_at_migration.sql first.

-- ─── 1. PRIMARY sync index: (updated_at ASC, polymer ASC) ────────────────────
--
-- This composite index serves all three query shapes used by _stream_sync():
--
--   a) COUNT(*) WHERE updated_at > :since
--      → Index range scan on updated_at alone (leading column).
--
--   b) First-page batch query:
--        WHERE updated_at > :since
--        ORDER BY updated_at ASC, polymer ASC  LIMIT :n
--      → Index range scan; ORDER BY resolved by index; no filesort.
--
--   c) Keyset resume batch query:
--        WHERE updated_at > :since
--          AND (updated_at > :last_ts
--               OR (updated_at = :last_ts AND polymer > :last_poly))
--        ORDER BY updated_at ASC, polymer ASC  LIMIT :n
--      → Index seek to (:last_ts, :last_poly), then forward scan.
--        O(log N) regardless of how many rows were already delivered.
--
-- Without this index MySQL does a full table scan for every query — with
-- 100 K rows that means scanning ~67 M rows per sync on average.

ALTER TABLE filtered_polymers
    DROP INDEX IF EXISTS idx_fp_updated_at_polymer;

ALTER TABLE filtered_polymers
    ADD INDEX idx_fp_updated_at_polymer (updated_at ASC, polymer ASC)
    COMMENT 'Covers SSE sync keyset pagination (updated_at > since ORDER BY updated_at, polymer)';


-- ─── 2. Category filter index: (category ASC, polymer ASC) ──────────────────
-- Covers: GET /api/v1/materials?category=:cat ORDER BY polymer LIMIT :n
-- Without this a category filter does a full scan and filesort.

ALTER TABLE filtered_polymers
    DROP INDEX IF EXISTS idx_fp_category_polymer;

ALTER TABLE filtered_polymers
    ADD INDEX idx_fp_category_polymer (category ASC, polymer ASC)
    COMMENT 'Covers category-filtered list queries with ORDER BY polymer';


-- ─── 3. Soft-delete index: (is_deleted) ──────────────────────────────────────
-- Covers admin and cleanup queries: WHERE is_deleted = 1

ALTER TABLE filtered_polymers
    DROP INDEX IF EXISTS idx_fp_is_deleted;

ALTER TABLE filtered_polymers
    ADD INDEX idx_fp_is_deleted (is_deleted)
    COMMENT 'Covers admin soft-delete queries';


-- ─── Verification ─────────────────────────────────────────────────────────────
-- Run this after the migration to confirm all indexes are in place.

SELECT
    INDEX_NAME,
    GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX SEPARATOR ', ') AS index_columns,
    NON_UNIQUE,
    INDEX_COMMENT
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME   = 'filtered_polymers'
  AND INDEX_NAME IN (
      'idx_fp_updated_at_polymer',
      'idx_fp_category_polymer',
      'idx_fp_is_deleted'
  )
GROUP BY INDEX_NAME, NON_UNIQUE, INDEX_COMMENT
ORDER BY INDEX_NAME;

-- Expected output (3 rows):
-- idx_fp_category_polymer  | category, polymer     | 1 | ...
-- idx_fp_is_deleted        | is_deleted            | 1 | ...
-- idx_fp_updated_at_polymer| updated_at, polymer   | 1 | ...
