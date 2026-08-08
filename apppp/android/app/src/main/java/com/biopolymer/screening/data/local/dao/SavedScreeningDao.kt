package com.biopolymer.screening.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.biopolymer.screening.data.local.entity.SavedScreeningEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SavedScreeningDao {

    @Query(
        """
        SELECT * FROM saved_screenings 
        WHERE isDeleted = 0 
          AND (:favoritesOnly = 0 OR isFavorite = 1)
          AND (:query = '' OR title LIKE '%' || :query || '%' OR topMaterialName LIKE '%' || :query || '%')
        ORDER BY 
          CASE WHEN :sortOrder = 'DATE_DESC' THEN updatedAt END DESC,
          CASE WHEN :sortOrder = 'DATE_ASC' THEN updatedAt END ASC,
          CASE WHEN :sortOrder = 'TITLE_ASC' THEN title END ASC,
          CASE WHEN :sortOrder = 'TITLE_DESC' THEN title END DESC,
          CASE WHEN :sortOrder = 'SCORE_DESC' THEN topMatchScore END DESC
        """
    )
    fun getSavedScreenings(
        query: String = "",
        sortOrder: String = "DATE_DESC",
        favoritesOnly: Boolean = false
    ): Flow<List<SavedScreeningEntity>>

    @Query("SELECT * FROM saved_screenings WHERE id = :id AND isDeleted = 0")
    suspend fun getScreeningById(id: String): SavedScreeningEntity?

    @Query("SELECT * FROM saved_screenings WHERE contentHash = :contentHash AND isDeleted = 0 LIMIT 1")
    suspend fun getScreeningByContentHash(contentHash: String): SavedScreeningEntity?

    @Query("SELECT * FROM saved_screenings WHERE LOWER(title) = LOWER(:title) AND isDeleted = 0 LIMIT 1")
    suspend fun getScreeningByTitle(title: String): SavedScreeningEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertScreening(screening: SavedScreeningEntity)

    @Update
    suspend fun updateScreening(screening: SavedScreeningEntity)

    @Query("UPDATE saved_screenings SET isDeleted = 1, deletedAt = :timestamp, updatedAt = :timestamp WHERE id = :id")
    suspend fun softDeleteScreening(id: String, timestamp: Long = System.currentTimeMillis())

    @Query("UPDATE saved_screenings SET isFavorite = :isFavorite, updatedAt = :updatedAt WHERE id = :id")
    suspend fun setFavorite(id: String, isFavorite: Boolean, updatedAt: Long = System.currentTimeMillis())

    @Query("SELECT * FROM saved_screenings WHERE isDeleted = 0")
    suspend fun getAllScreeningsSync(): List<SavedScreeningEntity>

    @Query("DELETE FROM saved_screenings")
    suspend fun deleteAll()
}
