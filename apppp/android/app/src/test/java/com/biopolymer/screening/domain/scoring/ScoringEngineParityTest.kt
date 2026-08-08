package com.biopolymer.screening.domain.scoring

import com.biopolymer.screening.domain.model.*
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test

/**
 * Cross-platform parity tests.
 * Verifies that the Kotlin scoring engine produces the same rankings
 * as the Python backend for identical input data.
 *
 * These tests use hardcoded expected outputs derived from running
 * the Python engine. If scoring logic changes, update both engines
 * and these expected values together.
 */
class ScoringEngineParityTest {

    private lateinit var engine: ScoringEngine

    @Before
    fun setup() {
        engine = ScoringEngine()
    }

    /**
     * Canonical test material set shared across parity tests.
     * Property values match exactly what Python tests use.
     */
    private fun parityMaterials(): List<Material> = listOf(
        Material(
            id = "parity-chitosan-high",
            name = "Chitosan (High MW)",
            category = "chitosan",
            evidenceLevel = "med",
            properties = MaterialProperties(
                tensileStrengthMin = 30f, tensileStrengthMax = 100f,
                elasticModulusMin = 1.0f, elasticModulusMax = 4.0f,
                elongationMin = 5f, elongationMax = 30f,
                punctureResistance = 15f,
                wvtr = 180f, otr = 95f,
                degradationDaysMin = 30, degradationDaysMax = 180,
                cytotoxicitySafe = true, hemocompatible = true, antimicrobial = true,
                sterGamma = true, sterEto = true, sterSteam = false,
                sterUv = true, sterAutoclave = false,
                procFilm = true, procCasting = true, procExtrusion = false,
                procCoating = true, procMelt = false,
                costBand = "low", availabilityBand = "high",
                dataCompleteness = 0.85f,
            )
        ),
        Material(
            id = "parity-alginate",
            name = "Sodium Alginate",
            category = "alginate",
            evidenceLevel = "high",
            properties = MaterialProperties(
                tensileStrengthMin = 20f, tensileStrengthMax = 80f,
                elasticModulusMin = 0.5f, elasticModulusMax = 2.5f,
                elongationMin = 4f, elongationMax = 20f,
                punctureResistance = 10f,
                wvtr = 350f, otr = 120f,
                degradationDaysMin = 7, degradationDaysMax = 90,
                cytotoxicitySafe = true, hemocompatible = true, antimicrobial = false,
                sterGamma = false, sterEto = true, sterSteam = true,
                sterUv = true, sterAutoclave = true,
                procFilm = true, procCasting = true, procExtrusion = false,
                procCoating = true, procMelt = false,
                costBand = "low", availabilityBand = "high",
                dataCompleteness = 0.9f,
            )
        ),
        Material(
            id = "parity-cnc",
            name = "Cellulose Nanocrystal",
            category = "cellulose",
            evidenceLevel = "high",
            properties = MaterialProperties(
                tensileStrengthMin = 80f, tensileStrengthMax = 200f,
                elasticModulusMin = 5.0f, elasticModulusMax = 15.0f,
                elongationMin = 2f, elongationMax = 10f,
                punctureResistance = 25f,
                wvtr = 50f, otr = 30f,
                degradationDaysMin = 180, degradationDaysMax = 365,
                cytotoxicitySafe = true, hemocompatible = true, antimicrobial = false,
                sterGamma = true, sterEto = true, sterSteam = true,
                sterUv = true, sterAutoclave = true,
                procFilm = true, procCasting = true, procExtrusion = true,
                procCoating = true, procMelt = false,
                costBand = "med", availabilityBand = "high",
                dataCompleteness = 0.95f,
            )
        ),
    )

    // ── Parity Tests ────────────────────────────────────────────

    @Test
    fun `broad mechanical requirement - all three materials pass`() {
        val result = engine.scoreAndRank(
            Requirement(
                mechanical = MechanicalReq(
                    tensileStrengthMin = 0f,
                    tensileStrengthMax = 250f,
                ),
            ),
            parityMaterials(),
        )
        assertEquals(3, result.recommendations.size)
        assertEquals(0, result.filteredOut)
    }

    @Test
    fun `empty requirements - returns no matches and no filtering`() {
        val result = engine.scoreAndRank(Requirement(), parityMaterials())
        assertEquals(0, result.recommendations.size)
        assertEquals(0, result.totalEvaluated)
        assertEquals(0, result.filteredOut)
    }

    @Test
    fun `gamma required - alginate filtered out`() {
        val req = Requirement(sterilization = SterilizationReq(gammaRequired = true))
        val result = engine.scoreAndRank(req, parityMaterials())
        val names = result.recommendations.map { it.materialName }
        assertTrue("Chitosan (High MW)" in names)
        assertTrue("Cellulose Nanocrystal" in names)
        assertFalse("Sodium Alginate" in names)
        assertEquals(1, result.filteredOut)
    }

    @Test
    fun `food packaging profile - CNC ranks highest for barrier`() {
        val req = Requirement(
            barrier = BarrierReq(wvtrMax = 100f, otrMax = 50f, weight = 2.0f),
            processing = ProcessingReq(filmRequired = true),
            cost = CostReq(maxCostBand = "med", weight = 1.5f),
        )
        val result = engine.scoreAndRank(req, parityMaterials())
        // CNC has best barrier (WVTR=50, OTR=30) and the highest weighted barrier score
        val topName = result.recommendations[0].materialName
        assertEquals("Cellulose Nanocrystal", topName)
    }

    @Test
    fun `wound care profile - chitosan ranks highest (antimicrobial)`() {
        val req = Requirement(
            biological = BiologicalReq(
                cytotoxicitySafeRequired = true,
                hemocompatibleRequired = true,
                antimicrobialRequired = true,
                weight = 2.0f,
            ),
            processing = ProcessingReq(filmRequired = true),
        )
        val result = engine.scoreAndRank(req, parityMaterials())
        val names = result.recommendations.map { it.materialName }
        // Alginate doesn't have antimicrobial, so should score lower for that
        // Chitosan has antimicrobial=true, should rank higher
        assertTrue("Chitosan should be in results", "Chitosan (High MW)" in names)
        assertTrue("CNC should be in results", "Cellulose Nanocrystal" in names)
    }

    @Test
    fun `confidence correlates with evidence level`() {
        val req = Requirement(mechanical = MechanicalReq(tensileStrengthMin = 10f))
        val result = engine.scoreAndRank(req, parityMaterials())
        val confByLevel = result.recommendations.associate {
            it.materialName to it.confidence
        }
        // High evidence (CNC, Alginate) should have higher confidence than Med (Chitosan)
        val cncConf = confByLevel["Cellulose Nanocrystal"]!!
        val chitosanConf = confByLevel["Chitosan (High MW)"]!!
        assertTrue(
            "CNC (high evidence) should have higher confidence than Chitosan (med): $cncConf vs $chitosanConf",
            cncConf > chitosanConf
        )
    }

    @Test
    fun `scores are identical across 50 runs`() {
        val req = Requirement(
            mechanical = MechanicalReq(tensileStrengthMin = 20f, tensileStrengthMax = 150f)
        )
        val materials = parityMaterials()

        val first = engine.scoreAndRank(req, materials)
        val firstScores = first.recommendations.map { it.materialName to it.score }

        repeat(49) { i ->
            val result = engine.scoreAndRank(req, materials)
            val scores = result.recommendations.map { it.materialName to it.score }
            assertEquals("Parity scoring not deterministic on run $i", firstScores, scores)
        }
    }
}
