-- =============================================================================
-- BioPolymer Backend — MySQL Schema Migration Script
-- =============================================================================
-- Run this script once against your MySQL database to create all required
-- tables.  It is fully idempotent: running it multiple times is safe.
--
-- Usage:
--   mysql -h <host> -u <user> -p <database> < scripts/migrate.sql
--
-- Or from the mysql prompt:
--   USE polysaccharide_selector;
--   SOURCE scripts/migrate.sql;
-- =============================================================================

SET NAMES utf8mb4;
SET time_zone = '+00:00';

-- ---------------------------------------------------------------------------
-- 1. Material catalog
--    Populated by importing your CSV / via the admin import endpoint.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `filtered_polymers` (
    `id`                    BIGINT          NOT NULL AUTO_INCREMENT,
    `polymer`               VARCHAR(255)    NOT NULL,
    `category`              VARCHAR(100)    NOT NULL DEFAULT 'unknown',
    `tensile_strength`      DOUBLE          DEFAULT NULL,
    `elastic_modulus`       DOUBLE          DEFAULT NULL,
    `elongation_pct`        DOUBLE          DEFAULT NULL,
    `flexibility`           DOUBLE          DEFAULT NULL,
    `wvtr`                  DOUBLE          DEFAULT NULL,
    `oxygen_permeability`   DOUBLE          DEFAULT NULL,
    `biocompatibility`      DOUBLE          DEFAULT NULL,
    `toxicity_score`        DOUBLE          DEFAULT NULL,
    `antimicrobial`         TINYINT(1)      DEFAULT 0,
    `biodegradation_days`   DOUBLE          DEFAULT NULL,
    `environmental_impact`  DOUBLE          DEFAULT NULL,
    `solubility`            VARCHAR(50)     DEFAULT NULL,
    `film_forming`          TINYINT(1)      DEFAULT 0,
    `sterilization_gamma`   TINYINT(1)      DEFAULT 0,
    `sterilization_eto`     TINYINT(1)      DEFAULT 0,
    `sterilization_steam`   TINYINT(1)      DEFAULT 0,
    `cost_band`             VARCHAR(20)     DEFAULT NULL,
    `availability_band`     VARCHAR(20)     DEFAULT NULL,
    `evidence_level`        VARCHAR(10)     NOT NULL DEFAULT 'low',
    `source_doi`            VARCHAR(255)    DEFAULT NULL,
    `is_augmented`          TINYINT(1)      NOT NULL DEFAULT 0,
    `suitability_label`     TINYINT(1)      DEFAULT NULL,
    `data_completeness`     FLOAT           NOT NULL DEFAULT 0,
    -- updated_at: bumped automatically on INSERT and UPDATE; used by
    -- the SSE delta-sync endpoint (WHERE updated_at > :since).
    -- The composite index idx_fp_updated_at_polymer covers this column.
    `updated_at`            DATETIME(6)     NOT NULL
                                DEFAULT CURRENT_TIMESTAMP(6)
                                ON UPDATE CURRENT_TIMESTAMP(6)
                                COMMENT 'Row last-modified; used by delta-sync',
    -- is_deleted: soft-delete flag.  Rows with is_deleted=1 are included
    -- in sync streams so clients can remove them from local storage.
    `is_deleted`            TINYINT(1)      NOT NULL DEFAULT 0
                                COMMENT '1 = soft-deleted',
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_polymer` (`polymer`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 2. Saved screening projects (Streamlit website)
--    Used by src/results_store.py
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `saved_projects` (
    `id`                BIGINT          NOT NULL AUTO_INCREMENT,
    `name`              VARCHAR(255)    NOT NULL,
    `created_at`        DATETIME        NOT NULL,
    `requirements`      LONGTEXT        NOT NULL,   -- JSON
    `ranked_materials`  LONGTEXT        NOT NULL,   -- JSON
    `request_id`        VARCHAR(255)    NOT NULL DEFAULT '',
    `pipeline_metadata` LONGTEXT        NOT NULL,   -- JSON
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 3. Users (FastAPI backend — Android + website auth)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `users` (
    `id`                VARCHAR(36)     NOT NULL,
    `auth_provider_id`  VARCHAR(255)    NOT NULL,
    `email`             VARCHAR(255)    DEFAULT NULL,
    `display_name`      VARCHAR(255)    DEFAULT NULL,
    `role`              VARCHAR(50)     NOT NULL DEFAULT 'user',
    `created_at`        DATETIME(6)     NOT NULL,
    `updated_at`        DATETIME(6)     NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_auth_provider_id` (`auth_provider_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 4. Projects (FastAPI backend — Android + website saved projects)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `projects` (
    `id`                VARCHAR(36)     NOT NULL,
    `user_id`           VARCHAR(36)     NOT NULL,
    `title`             VARCHAR(255)    NOT NULL,
    `requirements_json` LONGTEXT        NOT NULL DEFAULT (JSON_OBJECT()),
    `results_json`      LONGTEXT        DEFAULT NULL,
    `created_at`        DATETIME(6)     NOT NULL,
    `updated_at`        DATETIME(6)     NOT NULL,
    `is_deleted`        TINYINT(1)      NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    KEY `idx_projects_user_id` (`user_id`),
    KEY `idx_projects_updated_at` (`updated_at`),
    CONSTRAINT `fk_projects_user_id`
        FOREIGN KEY (`user_id`) REFERENCES `users` (`id`)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- 5. Indexes for common query patterns
-- ---------------------------------------------------------------------------
-- Speed up getAllProjects() queries (isDeleted=0 filter + date sort)
CREATE INDEX IF NOT EXISTS `idx_projects_user_deleted_updated`
    ON `projects` (`user_id`, `is_deleted`, `updated_at` DESC);

-- Speed up material catalog list queries (category filter + polymer sort)
CREATE INDEX IF NOT EXISTS `idx_polymers_category`
    ON `filtered_polymers` (`category`);

-- ---------------------------------------------------------------------------
-- 6. Sync performance indexes (required for streaming SSE delta-sync)
-- ---------------------------------------------------------------------------
-- PRIMARY sync index: covers the keyset pagination query shape used by the
-- streaming endpoint's _stream_sync() generator:
--
--   WHERE updated_at > :since
--     AND (updated_at > :last_ts OR (updated_at = :last_ts AND polymer > :last_poly))
--   ORDER BY updated_at ASC, polymer ASC
--   LIMIT :batch_size
--
-- Without this index MySQL performs a full table scan on every batch query.
-- With 100 K rows that means scanning millions of rows per sync session.
CREATE INDEX IF NOT EXISTS `idx_fp_updated_at_polymer`
    ON `filtered_polymers` (`updated_at` ASC, `polymer` ASC);

-- Category + polymer index: covers filtered list queries
--   WHERE category = :cat ORDER BY polymer LIMIT :n
CREATE INDEX IF NOT EXISTS `idx_fp_category_polymer`
    ON `filtered_polymers` (`category` ASC, `polymer` ASC);

-- Soft-delete index: covers admin cleanup queries WHERE is_deleted = 1
CREATE INDEX IF NOT EXISTS `idx_fp_is_deleted`
    ON `filtered_polymers` (`is_deleted`);

-- ---------------------------------------------------------------------------
-- Done.
-- ---------------------------------------------------------------------------
SELECT 'Migration complete.' AS status;
