package com.biopolymer.screening.data.local.dao

import androidx.room.*
import com.biopolymer.screening.data.local.entity.ProjectEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ProjectDao {

    @Query("SELECT * FROM projects WHERE isDeleted = 0 ORDER BY updatedAt DESC")
    fun getAllProjects(): Flow<List<ProjectEntity>>

    @Query("SELECT * FROM projects WHERE id = :id")
    suspend fun getProjectById(id: String): ProjectEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertProject(project: ProjectEntity)

    @Update
    suspend fun updateProject(project: ProjectEntity)

    @Query("UPDATE projects SET isDeleted = 1, updatedAt = :timestamp WHERE id = :id")
    suspend fun softDeleteProject(id: String, timestamp: Long = System.currentTimeMillis())

    @Query("SELECT * FROM projects WHERE isSynced = 0 AND userId IS NOT NULL")
    suspend fun getUnsyncedProjects(): List<ProjectEntity>

    @Query("UPDATE projects SET isSynced = 1 WHERE id = :id")
    suspend fun markSynced(id: String)

    @Query("SELECT * FROM projects")
    suspend fun getAllProjectsSync(): List<ProjectEntity>

    @Query("DELETE FROM projects")
    suspend fun deleteAllProjects()
}
