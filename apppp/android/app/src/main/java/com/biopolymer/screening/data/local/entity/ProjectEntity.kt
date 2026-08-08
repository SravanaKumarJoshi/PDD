package com.biopolymer.screening.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

/**
 * Room entity for a saved screening project.
 *
 * resultsJson stores the complete ScoringResult JSON produced by the
 * screening engine.  It is declared as a non-null String (defaulting to
 * an empty string rather than null) so Room never silently drops it when
 * the column type is omitted from a partial INSERT.
 *
 * DB schema version: 2
 * Migration from v1 → v2: resultsJson changed from nullable TEXT to
 * NOT NULL TEXT DEFAULT ''.  See AppDatabase for the migration object.
 */
@Entity(tableName = "projects")
data class ProjectEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "userId")
    val userId: String? = null,

    @ColumnInfo(name = "title")
    val title: String,

    /** Full JSON of the Requirement object used for this screening. */
    @ColumnInfo(name = "requirementsJson")
    val requirementsJson: String = "",

    /**
     * Full JSON of ScoringEngine.ScoringResult.
     *
     * Empty string ("") means the project was saved before a screening was
     * run, or the serialisation failed.  The UI and loadProject() handle
     * this by falling back to re-running the scoring engine.
     *
     * NOT nullable — Room maps SQL NULL from old rows to "" via the
     * defaultValue, preventing NullPointerException on read.
     */
    @ColumnInfo(name = "resultsJson", defaultValue = "")
    val resultsJson: String = "",

    @ColumnInfo(name = "createdAt")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updatedAt")
    val updatedAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "isSynced")
    val isSynced: Boolean = false,

    @ColumnInfo(name = "isDeleted")
    val isDeleted: Boolean = false,
)
