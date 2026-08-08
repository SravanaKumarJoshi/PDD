package com.biopolymer.screening.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entity for biopolymer materials.
 * Mirrors the backend `materials` table for offline access.
 */
@Entity(
    tableName = "materials",
    indices = [
        Index(value = ["name"]),
        Index(value = ["category"])
    ]
)
data class MaterialEntity(
    @PrimaryKey val id: String,
    val name: String,
    val category: String,
    val source: String? = null,
    val notes: String? = null,
    val evidenceLevel: String = "low",
    val referencesJson: String = "[]",
    val extPropertiesJson: String = "{}",
    val updatedAt: Long = System.currentTimeMillis(),
    val isDeleted: Boolean = false
)
