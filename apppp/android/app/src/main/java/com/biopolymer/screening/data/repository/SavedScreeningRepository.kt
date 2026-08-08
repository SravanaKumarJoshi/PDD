package com.biopolymer.screening.data.repository

import com.biopolymer.screening.domain.model.Requirement
import com.biopolymer.screening.domain.model.SavedScreening
import com.biopolymer.screening.domain.scoring.ScoringEngine
import kotlinx.coroutines.flow.Flow

enum class SavedScreeningSortOrder {
    NEWEST_FIRST,
    OLDEST_FIRST,
    TITLE_ASC,
    TITLE_DESC,
    MATCH_SCORE_DESC
}

sealed interface SaveScreeningResult {
    data class Success(val savedScreening: SavedScreening) : SaveScreeningResult
    data class DuplicateDetected(val existingScreening: SavedScreening) : SaveScreeningResult
    data class Error(val message: String, val cause: Throwable? = null) : SaveScreeningResult
}

interface SavedScreeningRepository {
    fun getSavedScreenings(
        query: String = "",
        sortOrder: SavedScreeningSortOrder = SavedScreeningSortOrder.NEWEST_FIRST,
        favoritesOnly: Boolean = false
    ): Flow<List<SavedScreening>>

    suspend fun getScreeningById(id: String): Result<SavedScreening?>

    suspend fun saveScreening(
        title: String,
        requirement: Requirement,
        scoringResult: ScoringEngine.ScoringResult,
        rawResponseJson: String? = null,
        overwriteIfExists: Boolean = false
    ): SaveScreeningResult

    suspend fun updateScreening(screening: SavedScreening): Result<Unit>

    suspend fun deleteScreening(id: String): Result<Unit>

    suspend fun toggleFavorite(id: String): Result<Boolean>

    suspend fun renameScreening(id: String, newTitle: String): Result<Unit>

    suspend fun syncWithBackend(): Result<Unit>
}
