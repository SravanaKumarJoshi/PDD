package com.biopolymer.screening.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Dedicated Room entity representing a saved screening result in local SQLite database.
 * Stores light summary fields for instant list queries alongside the full requirement and response payloads.
 */
@Entity(
    tableName = "saved_screenings",
    indices = [
        Index(value = ["createdAt"]),
        Index(value = ["updatedAt"]),
        Index(value = ["title"]),
        Index(value = ["isFavorite"]),
        Index(value = ["isArchived"]),
        Index(value = ["contentHash"]),
        Index(value = ["isDeleted"]),
    ]
)
data class SavedScreeningEntity(
    @PrimaryKey
    @ColumnInfo(name = "id")
    val id: String,

    @ColumnInfo(name = "projectId")
    val projectId: String? = null,

    @ColumnInfo(name = "title")
    val title: String,

    @ColumnInfo(name = "notes", defaultValue = "")
    val notes: String = "",

    @ColumnInfo(name = "tags", defaultValue = "")
    val tags: String = "",

    @ColumnInfo(name = "isFavorite", defaultValue = "0")
    val isFavorite: Boolean = false,

    @ColumnInfo(name = "isArchived", defaultValue = "0")
    val isArchived: Boolean = false,

    @ColumnInfo(name = "isDeleted", defaultValue = "0")
    val isDeleted: Boolean = false,

    @ColumnInfo(name = "deletedAt")
    val deletedAt: Long? = null,

    @ColumnInfo(name = "contentHash", defaultValue = "")
    val contentHash: String = "",

    @ColumnInfo(name = "topMaterialName", defaultValue = "")
    val topMaterialName: String = "",

    @ColumnInfo(name = "topMatchScore", defaultValue = "0.0")
    val topMatchScore: Float = 0f,

    @ColumnInfo(name = "safetyScore", defaultValue = "0.0")
    val safetyScore: Float = 0f,

    @ColumnInfo(name = "summaryText", defaultValue = "")
    val summaryText: String = "",

    @ColumnInfo(name = "requirementsJson", defaultValue = "")
    val requirementsJson: String = "",

    @ColumnInfo(name = "rawBackendResponseJson", defaultValue = "")
    val rawBackendResponseJson: String = "",

    @ColumnInfo(name = "schemaVersion", defaultValue = "1")
    val schemaVersion: Int = 1,

    @ColumnInfo(name = "apiVersion", defaultValue = "1.0")
    val apiVersion: String = "1.0",

    @ColumnInfo(name = "createdAt")
    val createdAt: Long = System.currentTimeMillis(),

    @ColumnInfo(name = "updatedAt")
    val updatedAt: Long = System.currentTimeMillis()
)
