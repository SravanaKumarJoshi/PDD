package com.biopolymer.screening.domain.scoring

import com.biopolymer.screening.domain.model.*
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * On-device transparent weighted scoring engine.
 * Mirrors the backend Python implementation for offline use.
 *
 * Pipeline:
 * 1. Hard constraint filtering
 * 2. Numeric range scoring
 * 3. Boolean/categorical scoring
 * 4. Weighted aggregation
 * 5. Confidence computation
 * 6. Explanation generation
 */
class ScoringEngine {

    data class FailedConstraint(
        val reason: String,
        val failureCount: Int
    )

    data class ScoringResult(
        val recommendations: List<Recommendation>,
        val totalEvaluated: Int,
        val filteredOut: Int,
        val limitingConstraints: List<FailedConstraint> = emptyList()
    )

    fun scoreAndRank(
        requirements: Requirement,
        materials: List<Material>,
    ): ScoringResult {
        if (!hasAnySelectedCharacteristic(requirements)) {
            return ScoringResult(
                recommendations = emptyList(),
                totalEvaluated = 0,
                filteredOut = 0,
                limitingConstraints = emptyList(),
            )
        }

        val scored = mutableListOf<ScoredMaterial>()
        var filteredCount = 0
        val failureCounts = mutableMapOf<String, Int>()

        for (material in materials) {
            val props = material.properties
            val sm = ScoredMaterial(material)

            // ── PHASE 1: Hard Constraint Filtering ──
            val reqS = requirements.sterilization
            if (reqS.gammaRequired && !props.sterGamma) sm.addFailure("Does not support gamma sterilization")
            if (reqS.etoRequired && !props.sterEto) sm.addFailure("Does not support EtO sterilization")
            if (reqS.steamRequired && !props.sterSteam) sm.addFailure("Does not support steam sterilization")
            if (reqS.uvRequired && !props.sterUv) sm.addFailure("Does not support UV sterilization")
            if (reqS.autoclaveRequired && !props.sterAutoclave) sm.addFailure("Does not support autoclave sterilization")

            val reqP = requirements.processing
            if (reqP.filmRequired && !props.procFilm) sm.addFailure("Cannot be processed as film")
            if (reqP.castingRequired && !props.procCasting) sm.addFailure("Does not support casting")
            if (reqP.extrusionRequired && !props.procExtrusion) sm.addFailure("Does not support extrusion")
            if (reqP.coatingRequired && !props.procCoating) sm.addFailure("Does not support coating")
            if (reqP.meltRequired && !props.procMelt) sm.addFailure("Does not support melt processing")

            val reqB = requirements.biological
            if (reqB.cytotoxicitySafeRequired && props.cytotoxicitySafe != true) sm.addFailure("Does not meet cytotoxicity safety requirement")
            if (reqB.hemocompatibleRequired && props.hemocompatible != true) sm.addFailure("Does not meet hemocompatibility requirement")

            if (sm.hardFailures.isNotEmpty()) {
                filteredCount++
                sm.hardFailures.forEach { reason ->
                    failureCounts[reason] = failureCounts.getOrDefault(reason, 0) + 1
                }
                continue
            }

            // ── PHASE 2: Numeric Range Scoring ──
            val reqM = requirements.mechanical
            sm.scores["tensile_strength"] = rangeOverlapScore(
                props.tensileStrengthMin, props.tensileStrengthMax,
                reqM.tensileStrengthMin, reqM.tensileStrengthMax
            )
            sm.scores["elastic_modulus"] = rangeOverlapScore(
                props.elasticModulusMin, props.elasticModulusMax,
                reqM.elasticModulusMin, reqM.elasticModulusMax
            )
            sm.scores["elongation"] = rangeOverlapScore(
                props.elongationMin, props.elongationMax,
                reqM.elongationMin, reqM.elongationMax
            )
            sm.scores["puncture_resistance"] = reqM.punctureResistanceMin?.let {
                inversePointScore(props.punctureResistance, it)
            }

            val reqBar = requirements.barrier
            sm.scores["wvtr"] = inversePointScore(props.wvtr, reqBar.wvtrMax)
            sm.scores["otr"] = inversePointScore(props.otr, reqBar.otrMax)

            val reqD = requirements.degradation
            sm.scores["degradation"] = rangeOverlapScore(
                props.degradationDaysMin?.toFloat(), props.degradationDaysMax?.toFloat(),
                reqD.degradationDaysMin?.toFloat(), reqD.degradationDaysMax?.toFloat()
            )

            // Hydrolytic stability (ordinal comparison, matching Python engine)
            val hydrolyticOrder = mapOf("low" to 1, "med" to 2, "high" to 3)
            sm.scores["hydrolytic_stability"] = if (
                reqD.hydrolyticStabilityMin != null && props.hydrolyticStability != null
            ) {
                val reqLevel = hydrolyticOrder[reqD.hydrolyticStabilityMin.lowercase()] ?: 1
                val actualLevel = hydrolyticOrder[props.hydrolyticStability.lowercase()] ?: 1
                if (actualLevel >= reqLevel) 1.0f else 0.3f
            } else {
                null
            }

            // Biocompatibility score
            val bioScores = mutableListOf<Float>()
            if (props.cytotoxicitySafe == true) bioScores.add(1.0f) else if (props.cytotoxicitySafe == false) bioScores.add(0.2f)
            if (props.hemocompatible == true) bioScores.add(1.0f) else if (props.hemocompatible == false) bioScores.add(0.3f)
            if (reqB.antimicrobialRequired) bioScores.add(if (props.antimicrobial == true) 1.0f else 0.0f)
            sm.scores["biocompatibility"] = if (bioScores.isNotEmpty()) bioScores.average().toFloat() else null

            // Cost
            val reqC = requirements.cost
            sm.scores["cost"] = bandScore(props.costBand, reqC.maxCostBand)
            sm.scores["availability"] = reqC.minAvailabilityBand?.let {
                bandScore(props.availabilityBand, it)
            }

            // ── PHASE 3: Weighted Aggregation ──
            val weightMap = mapOf(
                "tensile_strength" to reqM.weight,
                "elastic_modulus" to reqM.weight,
                "elongation" to reqM.weight,
                "puncture_resistance" to reqM.weight,
                "wvtr" to reqBar.weight,
                "otr" to reqBar.weight,
                "biocompatibility" to reqB.weight,
                "degradation" to reqD.weight,
                "hydrolytic_stability" to reqD.weight,
                "cost" to reqC.weight,
                "availability" to reqC.weight,
            )

            var totalWeighted = 0f
            var totalWeight = 0f

            for ((dim, score) in sm.scores) {
                val w = weightMap[dim] ?: 1.0f
                if (score == null) {
                    totalWeighted += w * 0.3f
                } else {
                    totalWeighted += w * score
                }
                totalWeight += w
            }

            sm.totalScore = if (totalWeight > 0) totalWeighted / totalWeight else 0f

            // ── PHASE 4: Confidence ──
            val evidenceMap = mapOf("low" to 0.4f, "med" to 0.7f, "high" to 1.0f)
            val evScore = evidenceMap[material.evidenceLevel] ?: 0.4f
            sm.confidence = 0.6f * props.dataCompleteness + 0.4f * evScore

            scored.add(sm)
        }

        // ── PHASE 5: Sort & Generate Explanations ──
        scored.sortByDescending { it.totalScore }

        val recommendations = scored.map { sm ->
            val contributions = sm.scores.entries
                .filter { it.value != null }
                .map { (dim, score) ->
                    FactorContribution(
                        factor = dim,
                        score = score!!,
                        description = describeFactor(dim, score)
                    )
                }
                .sortedByDescending { it.score }

            val tradeoffs = generateTradeoffs(sm)

            Recommendation(
                materialId = sm.material.id,
                materialName = sm.material.name,
                category = sm.material.category,
                score = sm.totalScore,
                confidence = sm.confidence,
                topFactors = contributions.take(5),
                concerns = contributions.filter { it.score < 0.4f }.take(3),
                unmetConstraints = sm.hardFailures,
                tradeoffs = tradeoffs,
            )
        }

        val limitingConstraints = failureCounts.map { (reason, count) ->
            FailedConstraint(reason = reason, failureCount = count)
        }.sortedByDescending { it.failureCount }

        return ScoringResult(
            recommendations = recommendations,
            totalEvaluated = materials.size,
            filteredOut = filteredCount,
            limitingConstraints = limitingConstraints
        )
    }

    private fun hasAnySelectedCharacteristic(requirements: Requirement): Boolean {
        val mechanical = requirements.mechanical
        val barrier = requirements.barrier
        val biological = requirements.biological
        val degradation = requirements.degradation
        val processing = requirements.processing
        val sterilization = requirements.sterilization
        val sustainability = requirements.sustainability
        val cost = requirements.cost

        return listOf(
            mechanical.tensileStrengthMin,
            mechanical.tensileStrengthMax,
            mechanical.elasticModulusMin,
            mechanical.elasticModulusMax,
            mechanical.elongationMin,
            mechanical.elongationMax,
            mechanical.punctureResistanceMin,
            barrier.wvtrMax,
            barrier.otrMax,
            degradation.degradationDaysMin,
            degradation.degradationDaysMax,
            degradation.hydrolyticStabilityMin,
            cost.maxCostBand,
            cost.minAvailabilityBand,
        ).any { it != null } ||
            biological.cytotoxicitySafeRequired ||
            biological.hemocompatibleRequired ||
            biological.antimicrobialRequired ||
            biological.lowEndotoxinRequired ||
            degradation.enzymaticRequired ||
            processing.filmRequired ||
            processing.castingRequired ||
            processing.extrusionRequired ||
            processing.coatingRequired ||
            processing.meltRequired ||
            sterilization.gammaRequired ||
            sterilization.etoRequired ||
            sterilization.steamRequired ||
            sterilization.uvRequired ||
            sterilization.autoclaveRequired ||
            sustainability.renewableRequired ||
            sustainability.compostableRequired
    }

    // ── Helper Functions ──

    private fun rangeOverlapScore(
        actualMin: Float?, actualMax: Float?,
        targetMin: Float?, targetMax: Float?,
    ): Float? {
        if (actualMin == null || actualMax == null || targetMin == null || targetMax == null) return null
        if (targetMax <= targetMin) return null

        val overlapStart = max(actualMin, targetMin)
        val overlapEnd = min(actualMax, targetMax)

        if (overlapStart > overlapEnd) {
            val gap = min(abs(actualMin - targetMax), abs(actualMax - targetMin))
            val targetSpan = targetMax - targetMin
            return max(0f, 1f - (gap / targetSpan))
        }

        val overlapLength = overlapEnd - overlapStart
        val targetLength = targetMax - targetMin
        return min(overlapLength / targetLength, 1f)
    }

    private fun inversePointScore(actualValue: Float?, targetMax: Float?): Float? {
        if (actualValue == null || targetMax == null || targetMax <= 0) return null
        if (actualValue <= targetMax) return 1.0f
        return min(targetMax / actualValue, 1.0f)
    }

    private fun bandScore(actualBand: String?, targetMaxBand: String?): Float? {
        if (actualBand == null || targetMaxBand == null) return null
        val bandOrder = mapOf("low" to 1, "med" to 2, "high" to 3)
        val actual = bandOrder[actualBand.lowercase()] ?: 2
        val target = bandOrder[targetMaxBand.lowercase()] ?: 3
        return if (actual <= target) 1.0f else 0.3f
    }

    private val factorLabels = mapOf(
        "tensile_strength" to "Tensile Strength",
        "elastic_modulus" to "Elastic Modulus",
        "elongation" to "Elongation at Break",
        "puncture_resistance" to "Puncture Resistance",
        "wvtr" to "Water Vapor Barrier (WVTR)",
        "otr" to "Oxygen Barrier (OTR)",
        "biocompatibility" to "Biocompatibility",
        "degradation" to "Degradation Timeline",
        "cost" to "Cost",
        "availability" to "Availability",
        "hydrolytic_stability" to "Hydrolytic Stability",
    )

    private fun describeFactor(dim: String, score: Float): String {
        val label = factorLabels[dim] ?: dim.replace("_", " ").replaceFirstChar { it.uppercase() }
        return when {
            score >= 0.9f -> "$label: Excellent match with target requirements"
            score >= 0.7f -> "$label: Good match, within acceptable range"
            score >= 0.4f -> "$label: Partial match, some deviation from target"
            else -> "$label: Poor match, significant gap from requirements"
        }
    }

    private fun generateTradeoffs(sm: ScoredMaterial): List<String> {
        val tradeoffs = mutableListOf<String>()
        val scores = sm.scores

        val mechAvg = listOfNotNull(scores["tensile_strength"], scores["elastic_modulus"])
            .takeIf { it.isNotEmpty() }?.average()?.toFloat()
        val barrierAvg = listOfNotNull(scores["wvtr"], scores["otr"])
            .takeIf { it.isNotEmpty() }?.average()?.toFloat()

        if (mechAvg != null && barrierAvg != null) {
            if (mechAvg > 0.7f && barrierAvg < 0.4f)
                tradeoffs.add("Strong mechanical properties but weak barrier performance — consider blending or coating")
            else if (barrierAvg > 0.7f && mechAvg < 0.4f)
                tradeoffs.add("Good barrier properties but limited mechanical strength — consider reinforcement")
        }

        if (sm.material.evidenceLevel == "low")
            tradeoffs.add("⚠ Evidence level is LOW — properties based on limited or synthetic data")

        val costScore = scores["cost"]
        if (costScore != null && costScore < 0.5f && sm.totalScore > 0.7f)
            tradeoffs.add("High-performing material but cost may be prohibitive — evaluate cost-benefit")

        return tradeoffs
    }

    private class ScoredMaterial(val material: Material) {
        val scores = mutableMapOf<String, Float?>()
        val hardFailures = mutableListOf<String>()
        var totalScore: Float = 0f
        var confidence: Float = 0f

        fun addFailure(msg: String) { hardFailures.add(msg) }
    }
}
