package com.biopolymer.screening.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase
import com.biopolymer.screening.data.local.dao.MaterialDao
import com.biopolymer.screening.data.local.dao.ProjectDao
import com.biopolymer.screening.data.local.dao.SavedScreeningDao
import com.biopolymer.screening.data.local.entity.MaterialEntity
import com.biopolymer.screening.data.local.entity.MaterialPropertyEntity
import com.biopolymer.screening.data.local.entity.ProjectEntity
import com.biopolymer.screening.data.local.entity.SavedScreeningEntity

/**
 * Room database — version history:
 *  v1  Initial schema
 *  v2  projects.resultsJson changed from nullable TEXT to TEXT NOT NULL DEFAULT ''
 *  v3  material_properties.degradationDaysMin and degradationDaysMax changed to REAL
 *  v4  Legacy sync metadata
 *  v5  Decommissioned legacy sync_metadata table
 *  v6  Added dedicated saved_screenings table with indices for persistence & offline reconstruction
 *  v7  Added indices on materials(name) and materials(category) for optimized search & catalog queries
 */
@Database(
    entities = [
        MaterialEntity::class,
        MaterialPropertyEntity::class,
        ProjectEntity::class,
        SavedScreeningEntity::class,
    ],
    version = 7,
    exportSchema = true,
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun materialDao(): MaterialDao
    abstract fun projectDao(): ProjectDao
    abstract fun savedScreeningDao(): SavedScreeningDao

    companion object {
        const val DATABASE_NAME = "biopolymer_screening_db"

        val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `projects_new` (
                        `id` TEXT NOT NULL,
                        `userId` TEXT,
                        `title` TEXT NOT NULL,
                        `requirementsJson` TEXT NOT NULL DEFAULT '',
                        `resultsJson` TEXT NOT NULL DEFAULT '',
                        `createdAt` INTEGER NOT NULL,
                        `updatedAt` INTEGER NOT NULL,
                        `isSynced` INTEGER NOT NULL DEFAULT 0,
                        `isDeleted` INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY(`id`)
                    )
                    """.trimIndent()
                )

                db.execSQL(
                    """
                    INSERT INTO `projects_new`
                        (`id`, `userId`, `title`, `requirementsJson`, `resultsJson`,
                         `createdAt`, `updatedAt`, `isSynced`, `isDeleted`)
                    SELECT
                        `id`,
                        `userId`,
                        `title`,
                        COALESCE(`requirementsJson`, ''),
                        COALESCE(`resultsJson`, ''),
                        `createdAt`,
                        `updatedAt`,
                        `isSynced`,
                        `isDeleted`
                    FROM `projects`
                    """.trimIndent()
                )

                db.execSQL("DROP TABLE IF EXISTS `projects` ")
                db.execSQL("ALTER TABLE `projects_new` RENAME TO `projects` ")
            }
        }

        val MIGRATION_2_3 = object : Migration(2, 3) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `material_properties_new` (
                        `id` TEXT NOT NULL,
                        `materialId` TEXT NOT NULL,
                        `tensileStrengthMpaMin` REAL,
                        `tensileStrengthMpaMax` REAL,
                        `elasticModulusGpaMin` REAL,
                        `elasticModulusGpaMax` REAL,
                        `elongationPctMin` REAL,
                        `elongationPctMax` REAL,
                        `punctureResistanceN` REAL,
                        `wvtr` REAL,
                        `otr` REAL,
                        `waterSolubility` INTEGER,
                        `swellingRatio` REAL,
                        `degradationDaysMin` REAL,
                        `degradationDaysMax` REAL,
                        `enzymaticDegradability` INTEGER,
                        `hydrolyticStability` TEXT,
                        `cytotoxicitySafe` INTEGER,
                        `hemocompatible` INTEGER,
                        `antimicrobial` INTEGER,
                        `endotoxinConcern` TEXT,
                        `sterGamma` INTEGER NOT NULL,
                        `sterEto` INTEGER NOT NULL,
                        `sterSteam` INTEGER NOT NULL,
                        `sterUv` INTEGER NOT NULL,
                        `sterAutoclave` INTEGER NOT NULL,
                        `procFilm` INTEGER NOT NULL,
                        `procCasting` INTEGER NOT NULL,
                        `procExtrusion` INTEGER NOT NULL,
                        `procCoating` INTEGER NOT NULL,
                        `procMelt` INTEGER NOT NULL,
                        `solventCompatible` TEXT,
                        `costBand` TEXT,
                        `availabilityBand` TEXT,
                        `dataCompleteness` REAL NOT NULL,
                        `updatedAt` INTEGER NOT NULL,
                        PRIMARY KEY(`id`),
                        FOREIGN KEY(`materialId`) REFERENCES `materials`(`id`)
                            ON DELETE CASCADE
                    )
                    """.trimIndent()
                )

                db.execSQL(
                    """
                    INSERT INTO `material_properties_new`
                    SELECT
                        `id`, `materialId`,
                        `tensileStrengthMpaMin`, `tensileStrengthMpaMax`,
                        `elasticModulusGpaMin`, `elasticModulusGpaMax`,
                        `elongationPctMin`, `elongationPctMax`,
                        `punctureResistanceN`,
                        `wvtr`, `otr`,
                        `waterSolubility`, `swellingRatio`,
                        CAST(`degradationDaysMin` AS REAL),
                        CAST(`degradationDaysMax` AS REAL),
                        `enzymaticDegradability`, `hydrolyticStability`,
                        `cytotoxicitySafe`, `hemocompatible`, `antimicrobial`,
                        `endotoxinConcern`,
                        `sterGamma`, `sterEto`, `sterSteam`, `sterUv`, `sterAutoclave`,
                        `procFilm`, `procCasting`, `procExtrusion`, `procCoating`, `procMelt`,
                        `solventCompatible`, `costBand`, `availabilityBand`,
                        `dataCompleteness`, `updatedAt`
                    FROM `material_properties`
                    """.trimIndent()
                )

                db.execSQL("DROP TABLE IF EXISTS `material_properties` ")
                db.execSQL("ALTER TABLE `material_properties_new` RENAME TO `material_properties` ")
                db.execSQL(
                    "CREATE UNIQUE INDEX IF NOT EXISTS `index_material_properties_materialId` " +
                        "ON `material_properties` (`materialId`)"
                )
            }
        }

        val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `sync_metadata` (
                        `id`        INTEGER NOT NULL,
                        `cursor`    TEXT,
                        `updatedAt` INTEGER NOT NULL,
                        PRIMARY KEY(`id`)
                    )
                    """.trimIndent()
                )
            }
        }

        val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("DROP TABLE IF EXISTS `sync_metadata` ")
            }
        }

        val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL(
                    """
                    CREATE TABLE IF NOT EXISTS `saved_screenings` (
                        `id` TEXT NOT NULL,
                        `projectId` TEXT,
                        `title` TEXT NOT NULL,
                        `notes` TEXT NOT NULL DEFAULT '',
                        `tags` TEXT NOT NULL DEFAULT '',
                        `isFavorite` INTEGER NOT NULL DEFAULT 0,
                        `isArchived` INTEGER NOT NULL DEFAULT 0,
                        `isDeleted` INTEGER NOT NULL DEFAULT 0,
                        `deletedAt` INTEGER,
                        `contentHash` TEXT NOT NULL DEFAULT '',
                        `topMaterialName` TEXT NOT NULL DEFAULT '',
                        `topMatchScore` REAL NOT NULL DEFAULT 0.0,
                        `safetyScore` REAL NOT NULL DEFAULT 0.0,
                        `summaryText` TEXT NOT NULL DEFAULT '',
                        `requirementsJson` TEXT NOT NULL DEFAULT '',
                        `rawBackendResponseJson` TEXT NOT NULL DEFAULT '',
                        `schemaVersion` INTEGER NOT NULL DEFAULT 1,
                        `apiVersion` TEXT NOT NULL DEFAULT '1.0',
                        `createdAt` INTEGER NOT NULL,
                        `updatedAt` INTEGER NOT NULL,
                        PRIMARY KEY(`id`)
                    )
                    """.trimIndent()
                )
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_createdAt` ON `saved_screenings` (`createdAt`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_updatedAt` ON `saved_screenings` (`updatedAt`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_title` ON `saved_screenings` (`title`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_isFavorite` ON `saved_screenings` (`isFavorite`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_isArchived` ON `saved_screenings` (`isArchived`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_contentHash` ON `saved_screenings` (`contentHash`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_saved_screenings_isDeleted` ON `saved_screenings` (`isDeleted`)")
            }
        }

        val MIGRATION_6_7 = object : Migration(6, 7) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_materials_name` ON `materials` (`name`)")
                db.execSQL("CREATE INDEX IF NOT EXISTS `index_materials_category` ON `materials` (`category`)")
            }
        }
    }
}

