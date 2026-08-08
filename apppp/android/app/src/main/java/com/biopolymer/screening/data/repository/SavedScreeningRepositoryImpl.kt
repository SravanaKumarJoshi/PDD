package com.biopolymer.screening.data.repository

import android.util.Log
import androidx.room.withTransaction
import com.biopolymer.screening.data.local.AppDatabase
import com.biopolymer.screening.data.local.dao.SavedScreeningDao
import com.biopolymer.screening.data.mapper.SavedScreeningMapper
import com.biopolymer.screening.domain.model.Requirement
import com.biopolymer.screening.domain.model.SavedScreening
import com.biopolymer.screening.domain.scoring.ScoringEngine
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "SavedScreeningRepo"

@Singleton
class SavedScreeningRepositoryImpl @Inject constructor(
    private val database: AppDatabase,
    private val dao: SavedScreeningDao,
    private val mapper: SavedScreeningMapper,
) : SavedScreeningRepository {

    override fun getSavedScreenings(
        query: String,
        sortOrder: SavedScreeningSortOrder,
        favoritesOnly: Boolean
    ): Flow<List<SavedScreening>> {
        val daoSortOrder = when (sortOrder) {
            SavedScreeningSortOrder.NEWEST_FIRST -> "DATE_DESC"
            SavedScreeningSortOrder.OLDEST_FIRST -> "DATE_ASC"
            SavedScreeningSortOrder.TITLE_ASC -> "TITLE_ASC"
            SavedScreeningSortOrder.TITLE_DESC -> "TITLE_DESC"
            SavedScreeningSortOrder.MATCH_SCORE_DESC -> "SCORE_DESC"
        }

        return dao.getSavedScreenings(
            query = query.trim(),
            sortOrder = daoSortOrder,
            favoritesOnly = favoritesOnly
        ).map { entities ->
            entities.map { entity -> mapper.toDomain(entity) }
        }
    }

    override suspend fun getScreeningById(id: String): Result<SavedScreening?> =
        withContext(Dispatchers.IO) {
            try {
                Log.d(TAG, "getScreeningById: Loading screening id=$id")
                val entity = dao.getScreeningById(id)
                if (entity != null) {
                    val domain = mapper.toDomain(entity)
                    Log.d(TAG, "getScreeningById: Load Successful for id=$id (title='${domain.title}')")
                    Result.success(domain)
                } else {
                    Log.w(TAG, "getScreeningById: Screening id=$id not found")
                    Result.success(null)
                }
            } catch (e: Exception) {
                Log.e(TAG, "getScreeningById: Failed to load screening id=$id", e)
                Result.failure(e)
            }
        }

    override suspend fun saveScreening(
        title: String,
        requirement: Requirement,
        scoringResult: ScoringEngine.ScoringResult,
        rawResponseJson: String?,
        overwriteIfExists: Boolean
    ): SaveScreeningResult = withContext(Dispatchers.IO) {
        val trimmedTitle = title.trim().ifBlank { "Screening Result" }
        Log.d(TAG, "saveScreening: Save Started for title='$trimmedTitle'")

        // 1. Validation
        if (scoringResult.recommendations.isEmpty()) {
            Log.w(TAG, "saveScreening: Validation Failed - Recommendations list is empty")
            return@withContext SaveScreeningResult.Error("Cannot save screening: No recommended materials in result.")
        }
        Log.d(TAG, "saveScreening: Validation Passed (${scoringResult.recommendations.size} recommendations)")

        // 2. Content Hash Computation
        val contentHash = mapper.computeContentHash(requirement, scoringResult)
        Log.d(TAG, "saveScreening: Fingerprint Computed - contentHash=$contentHash")

        // 3. Extract Summary Fields for Fast UI List Rendering
        val topRec = scoringResult.recommendations.firstOrNull()
        val topMaterialName = topRec?.materialName ?: "Unknown Material"
        val topMatchScore = topRec?.score ?: 0f
        val safetyScore = topRec?.confidence ?: 0f
        val summaryText = "${scoringResult.recommendations.size} materials matched out of ${scoringResult.totalEvaluated} evaluated"

        try {
            // 4. Room Transaction
            Log.d(TAG, "saveScreening: Transaction Started")
            val outcome = database.withTransaction {
                // Check if duplicate content hash exists
                val existingHash = dao.getScreeningByContentHash(contentHash)
                if (existingHash != null && !overwriteIfExists) {
                    val existingDomain = mapper.toDomain(existingHash)
                    Log.i(TAG, "saveScreening: Duplicate Detected by contentHash (${existingHash.id})")
                    return@withTransaction SaveScreeningResult.DuplicateDetected(existingDomain)
                }

                val now = System.currentTimeMillis()
                val targetId = if (existingHash != null && overwriteIfExists) {
                    existingHash.id
                } else {
                    UUID.randomUUID().toString()
                }

                val domainObject = SavedScreening(
                    id = targetId,
                    title = trimmedTitle,
                    contentHash = contentHash,
                    topMaterialName = topMaterialName,
                    topMatchScore = topMatchScore,
                    safetyScore = safetyScore,
                    summaryText = summaryText,
                    requirement = requirement,
                    scoringResult = scoringResult,
                    rawBackendResponseJson = rawResponseJson ?: "",
                    createdAt = existingHash?.createdAt ?: now,
                    updatedAt = now
                )

                val entity = mapper.toEntity(domainObject)
                dao.insertScreening(entity)

                // Verify insertion
                val verified = dao.getScreeningById(targetId)
                if (verified != null) {
                    Log.d(TAG, "saveScreening: Insert Successful - ID=$targetId, Title='$trimmedTitle'")
                    SaveScreeningResult.Success(mapper.toDomain(verified))
                } else {
                    Log.e(TAG, "saveScreening: Insert Failed - Database query post-insert returned null")
                    SaveScreeningResult.Error("Database insertion failed: Record not found after write.")
                }
            }
            outcome
        } catch (e: Exception) {
            Log.e(TAG, "saveScreening: Transaction Failed with Exception", e)
            SaveScreeningResult.Error("Failed to save screening: ${e.message}", e)
        }
    }

    override suspend fun updateScreening(screening: SavedScreening): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                Log.d(TAG, "updateScreening: Updating id=${screening.id}")
                val updatedDomain = screening.copy(updatedAt = System.currentTimeMillis())
                val entity = mapper.toEntity(updatedDomain)
                database.withTransaction {
                    dao.updateScreening(entity)
                }
                Log.d(TAG, "updateScreening: Update Successful for id=${screening.id}")
                Result.success(Unit)
            } catch (e: Exception) {
                Log.e(TAG, "updateScreening: Failed for id=${screening.id}", e)
                Result.failure(e)
            }
        }

    override suspend fun deleteScreening(id: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            try {
                Log.d(TAG, "deleteScreening: Soft deleting id=$id")
                database.withTransaction {
                    dao.softDeleteScreening(id, System.currentTimeMillis())
                }
                Log.d(TAG, "deleteScreening: Delete Successful for id=$id")
                Result.success(Unit)
            } catch (e: Exception) {
                Log.e(TAG, "deleteScreening: Failed to soft delete id=$id", e)
                Result.failure(e)
            }
        }

    override suspend fun toggleFavorite(id: String): Result<Boolean> =
        withContext(Dispatchers.IO) {
            try {
                database.withTransaction {
                    val existing = dao.getScreeningById(id)
                        ?: return@withTransaction Result.failure(Exception("Screening not found"))
                    val newFav = !existing.isFavorite
                    dao.setFavorite(id, newFav, System.currentTimeMillis())
                    Log.d(TAG, "toggleFavorite: Set favorite=$newFav for id=$id")
                    Result.success(newFav)
                }
            } catch (e: Exception) {
                Log.e(TAG, "toggleFavorite: Failed for id=$id", e)
                Result.failure(e)
            }
        }

    override suspend fun renameScreening(id: String, newTitle: String): Result<Unit> =
        withContext(Dispatchers.IO) {
            val title = newTitle.trim()
            if (title.isBlank()) return@withContext Result.failure(IllegalArgumentException("Title cannot be blank"))
            try {
                database.withTransaction {
                    val existing = dao.getScreeningById(id)
                        ?: return@withTransaction Result.failure(Exception("Screening not found"))
                    val updated = existing.copy(title = title, updatedAt = System.currentTimeMillis())
                    dao.updateScreening(updated)
                    Log.d(TAG, "renameScreening: Renamed id=$id to '$title'")
                    Result.success(Unit)
                }
            } catch (e: Exception) {
                Log.e(TAG, "renameScreening: Failed for id=$id", e)
                Result.failure(e)
            }
        }
}
