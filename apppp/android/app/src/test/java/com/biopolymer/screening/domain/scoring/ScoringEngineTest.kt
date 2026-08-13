package com.biopolymer.screening.domain.scoring

import com.biopolymer.screening.domain.model.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Unit tests for the on-device scoring engine.
 * Mirrors backend Python test coverage for cross-platform parity.
 */
class ScoringEngineTest {

    private lateinit var engine: ScoringEngine

    @Before
    fun setup() {
        engine = ScoringEngine()
    }

    // ── Helper ──────────────────────────────────────────────────

    private fun makeMaterial(
        name: String = "Test Material",
        category: String = "chitosan",
        evidenceLevel: String = "med",
        props: MaterialProperties = MaterialProperties(
            tensileStrengthMin = 30f,
            tensileStrengthMax = 100f,
            elasticModulusMin = 1.0f,
            elasticModulusMax = 4.0f,
            elongationMin = 5f,
            elongationMax = 30f,
            punctureResistance = 15f,
            wvtr = 180f,
            otr = 95f,
            degradationDaysMin = 30,
            degradationDaysMax = 180,
            cytotoxicitySafe = true,
            hemocompatible = true,
            antimicrobial = true,
            sterGamma = true,
            sterEto = true,
            sterSteam = false,
            sterUv = true,
            sterAutoclave = false,
            procFilm = true,
            procCasting = true,
            procExtrusion = false,
            procCoating = true,
            procMelt = false,
            costBand = "low",
            availabilityBand = "high",
            dataCompleteness = 0.85f,
        )
    ): Material = Material(
        id = "test-$name",
        name = name,
        category = category,
        evidenceLevel = evidenceLevel,
        properties = props,
    )

    private fun defaultReq() = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 10f))

    // ── Basic Scoring Tests ─────────────────────────────────────

    @Test
    fun `basic scoring produces positive score`() {
        val result = engine.scoreAndRank(defaultReq(), listOf(makeMaterial()))
        assertEquals(1, result.recommendations.size)
        assertTrue(result.recommendations[0].score > 0)
        assertTrue(result.recommendations[0].confidence > 0)
    }

    @Test
    fun `empty materials returns empty results`() {
        val result = engine.scoreAndRank(defaultReq(), emptyList())
        assertTrue(result.recommendations.isEmpty())
        assertEquals(0, result.totalEvaluated)
    }

    @Test
    fun `score and confidence in bounds`() {
        val materials = (1..10).map {
            makeMaterial(name = "Mat$it", props = MaterialProperties(
                tensileStrengthMin = (it * 10).toFloat(),
                tensileStrengthMax = (it * 20).toFloat(),
                wvtr = (it * 50).toFloat(),
                otr = (it * 30).toFloat(),
                costBand = "low",
                dataCompleteness = 0.7f,
            ))
        }
        val result = engine.scoreAndRank(defaultReq(), materials)
        for (rec in result.recommendations) {
            assertTrue("Score out of bounds: ${rec.score}", rec.score in 0f..100f)
            assertTrue("Confidence out of bounds: ${rec.confidence}", rec.confidence in 0f..1f)
        }
    }

    // ── Hard Constraint Filtering ───────────────────────────────

    @Test
    fun `steam required filters non-steam materials`() {
        val req = Requirement(sterilization = SterilizationReq(steamRequired = true))
        val materials = listOf(makeMaterial())  // ster_steam = false
        val result = engine.scoreAndRank(req, materials)
        assertEquals(0, result.recommendations.size)
        assertEquals(1, result.filteredOut)
    }

    @Test
    fun `gamma required keeps gamma materials`() {
        val req = Requirement(sterilization = SterilizationReq(gammaRequired = true))
        val gammaYes = makeMaterial(name = "GammaYes")  // ster_gamma = true
        val gammaNo = makeMaterial(name = "GammaNo", props = MaterialProperties(sterGamma = false))
        val result = engine.scoreAndRank(req, listOf(gammaYes, gammaNo))
        assertEquals(1, result.recommendations.size)
        assertEquals("GammaYes", result.recommendations[0].materialName)
    }

    @Test
    fun `multiple sterilization filters to intersection`() {
        val req = Requirement(sterilization = SterilizationReq(
            gammaRequired = true,
            steamRequired = true,
        ))
        val both = makeMaterial(name = "Both", props = MaterialProperties(
            sterGamma = true, sterSteam = true, dataCompleteness = 0.8f
        ))
        val gammaOnly = makeMaterial(name = "GammaOnly", props = MaterialProperties(
            sterGamma = true, sterSteam = false, dataCompleteness = 0.8f
        ))
        val result = engine.scoreAndRank(req, listOf(both, gammaOnly))
        assertEquals(1, result.recommendations.size)
        assertEquals("Both", result.recommendations[0].materialName)
    }

    @Test
    fun `film required filters non-film`() {
        val req = Requirement(processing = ProcessingReq(filmRequired = true))
        val filmYes = makeMaterial(name = "FilmYes")  // proc_film = true
        val filmNo = makeMaterial(name = "FilmNo", props = MaterialProperties(procFilm = false))
        val result = engine.scoreAndRank(req, listOf(filmYes, filmNo))
        assertEquals(1, result.recommendations.size)
        assertEquals("FilmYes", result.recommendations[0].materialName)
    }

    @Test
    fun `cytotoxicity required filters unsafe`() {
        val req = Requirement(biological = BiologicalReq(cytotoxicitySafeRequired = true))
        val safe = makeMaterial(name = "Safe")  // cytotoxicity_safe = true
        val unsafe = makeMaterial(name = "Unsafe", props = MaterialProperties(
            cytotoxicitySafe = false, dataCompleteness = 0.8f
        ))
        val result = engine.scoreAndRank(req, listOf(safe, unsafe))
        assertEquals(1, result.recommendations.size)
        assertEquals("Safe", result.recommendations[0].materialName)
    }

    // ── Ranking Order ───────────────────────────────────────────

    @Test
    fun `better matching material ranks higher`() {
        val req = Requirement(mechanical = MechanicalReq(
            tensileStrengthMin = 30f,
            tensileStrengthMax = 100f,
        ))
        val good = makeMaterial(name = "Good")  // tensile 30-100 matches perfectly
        val poor = makeMaterial(name = "Poor", props = MaterialProperties(
            tensileStrengthMin = 200f, tensileStrengthMax = 300f, dataCompleteness = 0.85f,
            procFilm = true, procCasting = true,
        ))
        val result = engine.scoreAndRank(req, listOf(good, poor))
        assertEquals(2, result.recommendations.size)
        assertEquals("Good", result.recommendations[0].materialName)
    }

    // ── Explanations ────────────────────────────────────────────

    @Test
    fun `explanations are generated`() {
        val result = engine.scoreAndRank(defaultReq(), listOf(makeMaterial()))
        val rec = result.recommendations[0]
        assertTrue(rec.topFactors.isNotEmpty())
        assertTrue(rec.topFactors.all { it.factor.isNotEmpty() && it.description.isNotEmpty() })
    }

    @Test
    fun `concerns list populated for poor matches`() {
        val req = Requirement(
            mechanical = MechanicalReq(
                tensileStrengthMin = 300f,
                tensileStrengthMax = 400f,
                weight = 2.0f,
            )
        )
        // Material has tensile 30-100, far from 200-400
        val result = engine.scoreAndRank(req, listOf(makeMaterial()))
        val rec = result.recommendations[0]
        // Should have some concerns for the poor tensile match
        // Concerns are factors with score < 50.0f
        assertTrue("Expected concerns for poor match", rec.concerns.isNotEmpty() || rec.topFactors.any { it.score < 50.0f })
    }

    // ── Determinism ─────────────────────────────────────────────

    @Test
    fun `deterministic over 100 runs`() {
        val materials = (1..10).map {
            makeMaterial(
                name = "Mat$it",
                props = MaterialProperties(
                    tensileStrengthMin = (it * 10).toFloat(),
                    tensileStrengthMax = (it * 20 + 50).toFloat(),
                    wvtr = (it * 40).toFloat(),
                    otr = (it * 25).toFloat(),
                    costBand = if (it % 2 == 0) "low" else "med",
                    dataCompleteness = it * 0.08f + 0.2f,
                    procFilm = true,
                    procCasting = true,
                )
            )
        }
        val req = Requirement(
            mechanical = MechanicalReq(tensileStrengthMin = 30f, tensileStrengthMax = 150f)
        )

        val firstResult = engine.scoreAndRank(req, materials)
        val firstScores = firstResult.recommendations.map { it.materialName to it.score }

        repeat(99) {
            val result = engine.scoreAndRank(req, materials)
            val scores = result.recommendations.map { it.materialName to it.score }
            assertEquals("Scoring not deterministic on run $it", firstScores, scores)
        }
    }

    // ── Tie Stability ───────────────────────────────────────────

    @Test
    fun `tied materials maintain insertion order`() {
        val matA = makeMaterial(name = "Alpha")
        val matB = makeMaterial(name = "Beta")
        val result = engine.scoreAndRank(defaultReq(), listOf(matA, matB))
        assertEquals(2, result.recommendations.size)
        assertEquals(result.recommendations[0].score, result.recommendations[1].score, 0.001f)
        assertEquals("Alpha", result.recommendations[0].materialName)
        assertEquals("Beta", result.recommendations[1].materialName)
    }

    // ── All-null properties ─────────────────────────────────────

    @Test
    fun `material with empty properties still scores`() {
        val mat = Material(
            id = "empty-1",
            name = "Empty Material",
            category = "unknown",
            evidenceLevel = "low",
            properties = MaterialProperties(),
        )
        val result = engine.scoreAndRank(defaultReq(), listOf(mat))
        assertEquals(1, result.recommendations.size)
        assertTrue(result.recommendations[0].score > 0f)
    }

    // ── Response shape ──────────────────────────────────────────

    @Test
    fun `result contains expected fields`() {
        val result = engine.scoreAndRank(defaultReq(), listOf(makeMaterial()))
        assertTrue(result.totalEvaluated > 0)
        assertEquals(0, result.filteredOut)

        val rec = result.recommendations[0]
        assertNotNull(rec.materialId)
        assertNotNull(rec.materialName)
        assertNotNull(rec.category)
        assertNotNull(rec.topFactors)
        assertNotNull(rec.concerns)
        assertNotNull(rec.unmetConstraints)
        assertNotNull(rec.tradeoffs)
    }
}
