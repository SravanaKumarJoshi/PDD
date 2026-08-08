package com.biopolymer.screening.data.repository

import android.util.Log
import com.biopolymer.screening.data.local.AppDatabase
import com.biopolymer.screening.data.local.dao.SavedScreeningDao
import com.biopolymer.screening.data.local.entity.SavedScreeningEntity
import com.biopolymer.screening.data.mapper.SavedScreeningMapper
import com.biopolymer.screening.domain.model.MechanicalReq
import com.biopolymer.screening.domain.model.Recommendation
import com.biopolymer.screening.domain.model.Requirement
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.mockk
import io.mockk.mockkStatic
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class SavedScreeningRepositoryTest {

    private val database: AppDatabase = mockk(relaxed = true)
    private val dao: SavedScreeningDao = mockk(relaxed = true)
    private lateinit var mapper: SavedScreeningMapper
    private lateinit var repository: SavedScreeningRepositoryImpl

    @Before
    fun setUp() {
        mockkStatic(Log::class)
        every { Log.d(any<String>(), any<String>()) } returns 0
        every { Log.w(any<String>(), any<String>()) } returns 0
        every { Log.i(any<String>(), any<String>()) } returns 0
        every { Log.e(any<String>(), any<String>()) } returns 0
        every { Log.e(any<String>(), any<String>(), any<Throwable>()) } returns 0

        val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
        mapper = SavedScreeningMapper(moshi)
        repository = SavedScreeningRepositoryImpl(database, dao, mapper)
    }

    @Test
    fun testSaveScreeningSuccess() = runBlocking {
        val req = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 10f))
        val scoringResult = ScoringEngine.ScoringResult(
            recommendations = listOf(
                Recommendation("m1", "Chitosan", "Polysaccharide", 0.88f, 0.9f)
            ),
            totalEvaluated = 5,
            filteredOut = 4
        )

        val hash = mapper.computeContentHash(req, scoringResult)
        coEvery { dao.getScreeningByContentHash(hash) } returns null
        coEvery { dao.getScreeningById(any()) } returns SavedScreeningEntity(
            id = "test-id",
            title = "Test Screening",
            contentHash = hash,
            topMaterialName = "Chitosan",
            topMatchScore = 0.88f,
            safetyScore = 0.9f,
            summaryText = "1 matched",
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )

        val result = repository.saveScreening("Test Screening", req, scoringResult)
        assertTrue("Expected Success but got $result", result is SaveScreeningResult.Success)
        coVerify(exactly = 1) { dao.insertScreening(any()) }
    }

    @Test
    fun testSaveScreeningEmptyRecommendationsFailsValidation() = runBlocking {
        val req = Requirement()
        val scoringResult = ScoringEngine.ScoringResult(recommendations = emptyList(), totalEvaluated = 0, filteredOut = 0)

        val result = repository.saveScreening("Empty Test", req, scoringResult)
        assertTrue("Expected Error but got $result", result is SaveScreeningResult.Error)
    }

    @Test
    fun testDuplicateDetection() = runBlocking {
        val req = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 10f))
        val scoringResult = ScoringEngine.ScoringResult(
            recommendations = listOf(Recommendation("m1", "Chitosan", "Polysaccharide", 0.88f, 0.9f)),
            totalEvaluated = 5,
            filteredOut = 4
        )

        val existingHash = mapper.computeContentHash(req, scoringResult)
        val existingEntity = SavedScreeningEntity(
            id = "existing-id",
            title = "Existing Screening",
            contentHash = existingHash,
            createdAt = System.currentTimeMillis(),
            updatedAt = System.currentTimeMillis()
        )

        coEvery { dao.getScreeningByContentHash(existingHash) } returns existingEntity

        val result = repository.saveScreening("Duplicate Test", req, scoringResult, overwriteIfExists = false)
        assertTrue("Expected DuplicateDetected but got $result", result is SaveScreeningResult.DuplicateDetected)
    }
}
