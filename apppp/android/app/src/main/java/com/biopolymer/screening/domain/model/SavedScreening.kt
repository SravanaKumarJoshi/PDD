package com.biopolymer.screening.domain.model

import com.biopolymer.screening.domain.scoring.ScoringEngine

/**
 * Domain model representing a complete saved biopolymer screening result.
 * Completely decoupled from database entity and framework dependencies.
 */
data class SavedScreening(
    val id: String,
    val projectId: String? = null,
    val title: String,
    val notes: String = "",
    val tags: List<String> = emptyList(),
    val isFavorite: Boolean = false,
    val isArchived: Boolean = false,
    val isDeleted: Boolean = false,
    val deletedAt: Long? = null,
    val contentHash: String,
    val topMaterialName: String = "",
    val topMatchScore: Float = 0f,
    val safetyScore: Float = 0f,
    val summaryText: String = "",
    val requirement: Requirement,
    val scoringResult: ScoringEngine.ScoringResult,
    val rawBackendResponseJson: String = "",
    val schemaVersion: Int = 1,
    val apiVersion: String = "1.0",
    val createdAt: Long = System.currentTimeMillis(),
    val updatedAt: Long = System.currentTimeMillis()
)
