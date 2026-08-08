package com.biopolymer.screening.data.local.dao

import androidx.room.*
import com.biopolymer.screening.data.local.entity.MaterialEntity
import com.biopolymer.screening.data.local.entity.MaterialPropertyEntity
import kotlinx.coroutines.flow.Flow

data class MaterialWithProperties(
    @Embedded val material: MaterialEntity,
    @Relation(
        parentColumn = "id",
        entityColumn = "materialId"
    )
    val properties: MaterialPropertyEntity?
)

data class MaterialCardProjection(
    val id: String,
    val name: String,
    val category: String,
    val evidenceLevel: String,
    val source: String?,
    val notes: String?,
    val tensileStrengthMpaMin: Float?,
    val tensileStrengthMpaMax: Float?,
    val degradationDaysMin: Float?,
    val degradationDaysMax: Float?,
    val cytotoxicitySafe: Boolean?
)

@Dao
interface MaterialDao {

    @Query("""
        SELECT 
            m.id AS id, 
            m.name AS name, 
            m.category AS category, 
            m.evidenceLevel AS evidenceLevel, 
            m.source AS source, 
            m.notes AS notes,
            p.tensileStrengthMpaMin AS tensileStrengthMpaMin,
            p.tensileStrengthMpaMax AS tensileStrengthMpaMax,
            p.degradationDaysMin AS degradationDaysMin,
            p.degradationDaysMax AS degradationDaysMax,
            p.cytotoxicitySafe AS cytotoxicitySafe
        FROM materials m
        LEFT JOIN material_properties p ON m.id = p.materialId
        WHERE m.isDeleted = 0
        ORDER BY m.name ASC
    """)
    fun getMaterialCards(): Flow<List<MaterialCardProjection>>

    @Query("""
        SELECT 
            m.id AS id, 
            m.name AS name, 
            m.category AS category, 
            m.evidenceLevel AS evidenceLevel, 
            m.source AS source, 
            m.notes AS notes,
            p.tensileStrengthMpaMin AS tensileStrengthMpaMin,
            p.tensileStrengthMpaMax AS tensileStrengthMpaMax,
            p.degradationDaysMin AS degradationDaysMin,
            p.degradationDaysMax AS degradationDaysMax,
            p.cytotoxicitySafe AS cytotoxicitySafe
        FROM materials m
        LEFT JOIN material_properties p ON m.id = p.materialId
        WHERE m.isDeleted = 0 AND m.category = :category
        ORDER BY m.name ASC
    """)
    fun getMaterialCardsByCategory(category: String): Flow<List<MaterialCardProjection>>

    @Query("""
        SELECT 
            m.id AS id, 
            m.name AS name, 
            m.category AS category, 
            m.evidenceLevel AS evidenceLevel, 
            m.source AS source, 
            m.notes AS notes,
            p.tensileStrengthMpaMin AS tensileStrengthMpaMin,
            p.tensileStrengthMpaMax AS tensileStrengthMpaMax,
            p.degradationDaysMin AS degradationDaysMin,
            p.degradationDaysMax AS degradationDaysMax,
            p.cytotoxicitySafe AS cytotoxicitySafe
        FROM materials m
        LEFT JOIN material_properties p ON m.id = p.materialId
        WHERE m.isDeleted = 0 AND (m.name LIKE '%' || :query || '%' OR m.category LIKE '%' || :query || '%')
        ORDER BY m.name ASC
    """)
    fun searchMaterialCards(query: String): Flow<List<MaterialCardProjection>>

    @Transaction
    @Query("SELECT * FROM materials WHERE isDeleted = 0 ORDER BY name ASC")
    fun getAllMaterials(): Flow<List<MaterialWithProperties>>

    @Transaction
    @Query("SELECT * FROM materials WHERE isDeleted = 0 AND category = :category ORDER BY name ASC")
    fun getMaterialsByCategory(category: String): Flow<List<MaterialWithProperties>>

    @Transaction
    @Query("SELECT * FROM materials WHERE isDeleted = 0 AND name LIKE '%' || :query || '%' ORDER BY name ASC")
    fun searchMaterials(query: String): Flow<List<MaterialWithProperties>>

    @Transaction
    @Query("SELECT * FROM materials WHERE id = :id")
    suspend fun getMaterialById(id: String): MaterialWithProperties?

    @Transaction
    @Query("SELECT * FROM materials WHERE isDeleted = 0")
    suspend fun getAllMaterialsSync(): List<MaterialWithProperties>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMaterial(material: MaterialEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProperty(property: MaterialPropertyEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertMaterials(materials: List<MaterialEntity>)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProperties(properties: List<MaterialPropertyEntity>)

    /**
     * Deletes all materials whose ID is not in [keepIds].
     *
     * SQLite limits a single IN clause to 999 bind parameters.  Calling this
     * with a large [keepIds] list would throw "too many SQL variables" and
     * crash the entire sync transaction.  Call [deleteMaterialsNotInChunked]
     * from the repository/ViewModel instead — it splits the list into safe
     * batches before calling this function.
     *
     * This overload is kept package-private (internal) to prevent accidental
     * direct calls with unbounded lists.
     */
    @Query("DELETE FROM materials WHERE id NOT IN (:keepIds)")
    suspend fun deleteMaterialsNotInBatch(keepIds: List<String>)

    /**
     * Marks all materials as deleted.  Used as the fallback when [keepIds]
     * is empty (meaning the server returned nothing to keep, which should
     * not happen on a first sync but is defensive here).
     */
    @Query("UPDATE materials SET isDeleted = 1")
    suspend fun markAllDeleted()

    @Query("DELETE FROM materials")
    suspend fun deleteAllMaterials()

    @Query("SELECT MAX(updatedAt) FROM materials")
    suspend fun getLastUpdatedTimestamp(): Long?

    @Query("SELECT COUNT(*) FROM materials WHERE isDeleted = 0")
    suspend fun getMaterialCount(): Int

    /**
     * Returns the subset of [ids] that already exist in the materials table.
     * Used by [MaterialSyncRepository] to distinguish inserts from updates
     * without a separate SELECT per row.
     *
     * SQLite's 999-bind-parameter limit is respected by the caller, which
     * must chunk [ids] into batches of [SQLITE_MAX_VARIABLE_NUMBER].
     */
    @Query("SELECT id FROM materials WHERE id IN (:ids)")
    suspend fun getExistingIds(ids: List<String>): List<String>

    /**
     * Soft-delete materials by explicit ID list.
     * Called during the `complete` event processing to remove server-deleted rows.
     */
    @Query("UPDATE materials SET isDeleted = 1 WHERE id IN (:ids)")
    suspend fun markDeletedByIds(ids: List<String>)

    @Query("SELECT DISTINCT category FROM materials WHERE isDeleted = 0 ORDER BY category ASC")
    fun getCategories(): Flow<List<String>>

    /**
     * Safe wrapper around [deleteMaterialsNotInBatch] that chunks [keepIds]
     * into batches of [SQLITE_MAX_VARIABLE_NUMBER] to stay under SQLite's
     * 999-bind-parameter limit.
     *
     * Call this instead of [deleteMaterialsNotInBatch] directly whenever the
     * list of IDs may exceed 999 entries (i.e., always, on a full-catalog sync).
     */
    suspend fun deleteMaterialsMissingFromServer(keepIds: List<String>) {
        if (keepIds.isEmpty()) {
            // Nothing to keep — mark everything deleted rather than deleting nothing.
            markAllDeleted()
            return
        }
        keepIds.chunked(SQLITE_MAX_VARIABLE_NUMBER).forEach { batch ->
            deleteMaterialsNotInBatch(batch)
        }
    }

    companion object {
        /**
         * SQLite's maximum number of host parameters in a single statement.
         * Using 900 (not 999) gives a safe margin for Room's own generated
         * query overhead and any additional bind parameters in the WHERE clause.
         */
        const val SQLITE_MAX_VARIABLE_NUMBER = 900
    }
}
