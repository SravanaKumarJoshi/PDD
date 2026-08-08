package com.biopolymer.screening.data.mapper

import android.util.Log
import com.biopolymer.screening.data.local.entity.SavedScreeningEntity
import com.biopolymer.screening.domain.model.Requirement
import com.biopolymer.screening.domain.model.SavedScreening
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.security.MessageDigest
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "SavedScreeningMapper"

@Singleton
class SavedScreeningMapper @Inject constructor(
    private val moshi: Moshi
) {
    private val reqAdapter by lazy { moshi.adapter(Requirement::class.java) }
    private val resultAdapter by lazy { moshi.adapter(ScoringEngine.ScoringResult::class.java) }

    /**
     * Map Room entity to Domain Model.
     * Operates safely with fallbacks so corrupted or missing fields never crash the application.
     */
    fun toDomain(entity: SavedScreeningEntity): SavedScreening {
        val requirement = try {
            if (entity.requirementsJson.isNotBlank()) {
                reqAdapter.fromJson(entity.requirementsJson) ?: Requirement()
            } else Requirement()
        } catch (e: Exception) {
            Log.e(TAG, "Error deserializing requirement for ID ${entity.id}", e)
            Requirement()
        }

        val scoringResult = try {
            if (entity.rawBackendResponseJson.isNotBlank()) {
                resultAdapter.fromJson(entity.rawBackendResponseJson) ?: ScoringEngine.ScoringResult(emptyList(), 0, 0)
            } else {
                ScoringEngine.ScoringResult(emptyList(), 0, 0)
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error deserializing scoring result for ID ${entity.id}", e)
            ScoringEngine.ScoringResult(emptyList(), 0, 0)
        }

        val tagsList = if (entity.tags.isBlank()) emptyList() else entity.tags.split(",").map { it.trim() }

        return SavedScreening(
            id = entity.id,
            projectId = entity.projectId,
            title = entity.title,
            notes = entity.notes,
            tags = tagsList,
            isFavorite = entity.isFavorite,
            isArchived = entity.isArchived,
            isDeleted = entity.isDeleted,
            deletedAt = entity.deletedAt,
            contentHash = entity.contentHash,
            topMaterialName = entity.topMaterialName,
            topMatchScore = entity.topMatchScore,
            safetyScore = entity.safetyScore,
            summaryText = entity.summaryText,
            requirement = requirement,
            scoringResult = scoringResult,
            rawBackendResponseJson = entity.rawBackendResponseJson,
            schemaVersion = entity.schemaVersion,
            apiVersion = entity.apiVersion,
            createdAt = entity.createdAt,
            updatedAt = entity.updatedAt
        )
    }

    /**
     * Map Domain Model to Room entity.
     */
    fun toEntity(domain: SavedScreening): SavedScreeningEntity {
        val reqJson = try {
            reqAdapter.toJson(domain.requirement)
        } catch (e: Exception) {
            Log.e(TAG, "Error serializing requirement for ID ${domain.id}", e)
            ""
        }

        val responseJson = if (domain.rawBackendResponseJson.isNotBlank()) {
            domain.rawBackendResponseJson
        } else {
            try {
                resultAdapter.toJson(domain.scoringResult)
            } catch (e: Exception) {
                Log.e(TAG, "Error serializing scoring result for ID ${domain.id}", e)
                ""
            }
        }

        val tagsString = domain.tags.joinToString(",")

        return SavedScreeningEntity(
            id = domain.id,
            projectId = domain.projectId,
            title = domain.title,
            notes = domain.notes,
            tags = tagsString,
            isFavorite = domain.isFavorite,
            isArchived = domain.isArchived,
            isDeleted = domain.isDeleted,
            deletedAt = domain.deletedAt,
            contentHash = domain.contentHash.ifBlank { computeContentHash(domain.requirement, domain.scoringResult) },
            topMaterialName = domain.topMaterialName,
            topMatchScore = domain.topMatchScore,
            safetyScore = domain.safetyScore,
            summaryText = domain.summaryText,
            requirementsJson = reqJson,
            rawBackendResponseJson = responseJson,
            schemaVersion = domain.schemaVersion,
            apiVersion = domain.apiVersion,
            createdAt = domain.createdAt,
            updatedAt = domain.updatedAt
        )
    }

    /**
     * Compute a deterministic SHA-256 content hash fingerprint from screening requirement & top results.
     */
    fun computeContentHash(requirement: Requirement, scoringResult: ScoringEngine.ScoringResult): String {
        val topMaterialsKey = scoringResult.recommendations.take(5).joinToString("|") { "${it.materialId}:${it.score}" }
        val reqKey = requirement.toString()
        val rawInput = "$reqKey#$topMaterialsKey"

        return try {
            val digest = MessageDigest.getInstance("SHA-256")
            val hashBytes = digest.digest(rawInput.toByteArray(Charsets.UTF_8))
            hashBytes.joinToString("") { "%02x".format(it) }
        } catch (e: Exception) {
            Log.e(TAG, "Error computing content hash", e)
            rawInput.hashCode().toString()
        }
    }
}
