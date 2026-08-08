package com.biopolymer.screening.data.mapper

import android.util.Log
import com.biopolymer.screening.domain.model.MechanicalReq
import com.biopolymer.screening.domain.model.Recommendation
import com.biopolymer.screening.domain.model.Requirement
import com.biopolymer.screening.domain.model.SavedScreening
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import io.mockk.every
import io.mockk.mockkStatic
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import java.util.UUID

class SavedScreeningMapperTest {

    private lateinit var moshi: Moshi
    private lateinit var mapper: SavedScreeningMapper

    @Before
    fun setUp() {
        mockkStatic(Log::class)
        every { Log.d(any<String>(), any<String>()) } returns 0
        every { Log.w(any<String>(), any<String>()) } returns 0
        every { Log.i(any<String>(), any<String>()) } returns 0
        every { Log.e(any<String>(), any<String>()) } returns 0
        every { Log.e(any<String>(), any<String>(), any<Throwable>()) } returns 0

        moshi = Moshi.Builder()
            .add(KotlinJsonAdapterFactory())
            .build()
        mapper = SavedScreeningMapper(moshi)
    }

    @Test
    fun testContentHashComputationIsDeterministic() {
        val req = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 15f))
        val scoringResult = ScoringEngine.ScoringResult(
            recommendations = listOf(
                Recommendation(
                    materialId = "mat-001",
                    materialName = "Chitosan",
                    category = "Polysaccharide",
                    score = 0.85f,
                    confidence = 0.9f
                )
            ),
            totalEvaluated = 10,
            filteredOut = 9
        )

        val hash1 = mapper.computeContentHash(req, scoringResult)
        val hash2 = mapper.computeContentHash(req, scoringResult)

        assertNotNull(hash1)
        assertTrue(hash1.isNotEmpty())
        assertEquals(hash1, hash2)
    }

    @Test
    fun testDomainToEntityAndBackMappingIntegrity() {
        val req = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 20f))
        val scoringResult = ScoringEngine.ScoringResult(
            recommendations = listOf(
                Recommendation(
                    materialId = "mat-002",
                    materialName = "Alginate",
                    category = "Polysaccharide",
                    score = 0.92f,
                    confidence = 0.95f
                )
            ),
            totalEvaluated = 15,
            filteredOut = 14
        )

        val originalDomain = SavedScreening(
            id = UUID.randomUUID().toString(),
            title = "Test Hydrogel Screening",
            contentHash = "hash-12345",
            topMaterialName = "Alginate",
            topMatchScore = 0.92f,
            safetyScore = 0.95f,
            summaryText = "1 matched out of 15",
            requirement = req,
            scoringResult = scoringResult,
            rawBackendResponseJson = ""
        )

        val entity = mapper.toEntity(originalDomain)
        val reconstructedDomain = mapper.toDomain(entity)

        assertEquals(originalDomain.id, reconstructedDomain.id)
        assertEquals(originalDomain.title, reconstructedDomain.title)
        assertEquals(originalDomain.topMaterialName, reconstructedDomain.topMaterialName)
        assertEquals(originalDomain.topMatchScore, reconstructedDomain.topMatchScore, 0.001f)
        assertEquals(originalDomain.scoringResult.recommendations.size, reconstructedDomain.scoringResult.recommendations.size)
        assertEquals(originalDomain.scoringResult.recommendations[0].materialName, reconstructedDomain.scoringResult.recommendations[0].materialName)
    }
}
