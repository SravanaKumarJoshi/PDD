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
 * 1. Active requirement detection & Hard constraint filtering
 * 2. Continuous numeric range/distance scoring (0.0f - 100.0f scale)
 * 3. Boolean/categorical scoring
 * 4. Weighted aggregation
 * 5. Confidence computation
 * 6. Explanation generation & Ranking
 */
class ScoringEngine {

    companion object {
        const val MISSING_DATA_SCORE_PENALTY = 25.0f
    }

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
        if (materials.isEmpty() || !hasAnySelectedCharacteristic(requirements)) {
            return ScoringResult(
                recommendations = emptyList(),
                totalEvaluated = materials.size,
                filteredOut = 0,
                limitingConstraints = emptyList(),
            )
        }

        // Active requirements and weights map
        val reqM = requirements.mechanical
        val reqBar = requirements.barrier
        val reqB = requirements.biological
        val reqD = requirements.degradation
        val reqP = requirements.processing
        val reqS = requirements.sterilization
        val reqC = requirements.cost

        val activeWeights = mutableMapOf<String, Float>()

        if (reqM.tensileStrengthMin != null || reqM.tensileStrengthMax != null) {
            activeWeights["tensile_strength"] = reqM.weight
        }
        if (reqM.elasticModulusMin != null || reqM.elasticModulusMax != null) {
            activeWeights["elastic_modulus"] = reqM.weight
        }
        if (reqM.elongationMin != null || reqM.elongationMax != null) {
            activeWeights["elongation"] = reqM.weight
        }
        if (reqM.punctureResistanceMin != null) {
            activeWeights["puncture_resistance"] = reqM.weight
        }

        if (reqBar.wvtrMax != null) {
            activeWeights["wvtr"] = reqBar.weight
        }
        if (reqBar.otrMax != null) {
            activeWeights["otr"] = reqBar.weight
        }

        if (reqD.degradationDaysMin != null || reqD.degradationDaysMax != null) {
            activeWeights["degradation"] = reqD.weight
        }
        if (reqD.hydrolyticStabilityMin != null) {
            activeWeights["hydrolytic_stability"] = reqD.weight
        }

        if (reqB.cytotoxicitySafeRequired || reqB.hemocompatibleRequired ||
            reqB.antimicrobialRequired || reqB.lowEndotoxinRequired
        ) {
            activeWeights["biocompatibility"] = reqB.weight
        }

        if (reqC.maxCostBand != null) {
            activeWeights["cost"] = reqC.weight
        }
        if (reqC.minAvailabilityBand != null) {
            activeWeights["availability"] = reqC.weight
        }

        val scored = mutableListOf<ScoredMaterial>()
        var filteredCount = 0
        val failureCounts = mutableMapOf<String, Int>()

        for (material in materials) {
            val props = material.properties
            val sm = ScoredMaterial(material)

            // ── PHASE 1: Hard Constraint Filtering ──
            if (reqS.gammaRequired && !props.sterGamma) sm.addFailure("Does not support gamma sterilization")
            if (reqS.etoRequired && !props.sterEto) sm.addFailure("Does not support EtO sterilization")
            if (reqS.steamRequired && !props.sterSteam) sm.addFailure("Does not support steam sterilization")
            if (reqS.uvRequired && !props.sterUv) sm.addFailure("Does not support UV sterilization")
            if (reqS.autoclaveRequired && !props.sterAutoclave) sm.addFailure("Does not support autoclave sterilization")

            if (reqP.filmRequired && !props.procFilm) sm.addFailure("Cannot be processed as film")
            if (reqP.castingRequired && !props.procCasting) sm.addFailure("Does not support casting")
            if (reqP.extrusionRequired && !props.procExtrusion) sm.addFailure("Does not support extrusion")
            if (reqP.coatingRequired && !props.procCoating) sm.addFailure("Does not support coating")
            if (reqP.meltRequired && !props.procMelt) sm.addFailure("Does not support melt processing")

            if (reqB.cytotoxicitySafeRequired && props.cytotoxicitySafe != true) sm.addFailure("Does not meet cytotoxicity safety requirement")
            if (reqB.hemocompatibleRequired && props.hemocompatible != true) sm.addFailure("Does not meet hemocompatibility requirement")

            if (sm.hardFailures.isNotEmpty()) {
                filteredCount++
                sm.hardFailures.forEach { reason ->
                    failureCounts[reason] = failureCounts.getOrDefault(reason, 0) + 1
                }
                continue
            }

            // ── PHASE 2: Continuous Numeric & Categorical Scoring ──
            if (activeWeights.containsKey("tensile_strength")) {
                sm.scores["tensile_strength"] = scoreRangeRequirement(
                    props.tensileStrengthMin, props.tensileStrengthMax,
                    reqM.tensileStrengthMin, reqM.tensileStrengthMax
                )
            }
            if (activeWeights.containsKey("elastic_modulus")) {
                sm.scores["elastic_modulus"] = scoreRangeRequirement(
                    props.elasticModulusMin, props.elasticModulusMax,
                    reqM.elasticModulusMin, reqM.elasticModulusMax
                )
            }
            if (activeWeights.containsKey("elongation")) {
                sm.scores["elongation"] = scoreRangeRequirement(
                    props.elongationMin, props.elongationMax,
                    reqM.elongationMin, reqM.elongationMax
                )
            }
            if (activeWeights.containsKey("puncture_resistance")) {
                sm.scores["puncture_resistance"] = scoreMinRequirement(
                    props.punctureResistance, reqM.punctureResistanceMin
                )
            }

            if (activeWeights.containsKey("wvtr")) {
                sm.scores["wvtr"] = scoreInversePoint(props.wvtr, reqBar.wvtrMax)
            }
            if (activeWeights.containsKey("otr")) {
                sm.scores["otr"] = scoreInversePoint(props.otr, reqBar.otrMax)
            }

            if (activeWeights.containsKey("degradation")) {
                sm.scores["degradation"] = scoreRangeRequirement(
                    props.degradationDaysMin?.toFloat(), props.degradationDaysMax?.toFloat(),
                    reqD.degradationDaysMin?.toFloat(), reqD.degradationDaysMax?.toFloat()
                )
            }
            if (activeWeights.containsKey("hydrolytic_stability")) {
                sm.scores["hydrolytic_stability"] = scoreOrdinalBand(
                    props.hydrolyticStability, reqD.hydrolyticStabilityMin, higherIsBetter = true
                )
            }

            if (activeWeights.containsKey("biocompatibility")) {
                val bioScores = mutableListOf<Float>()
                if (reqB.cytotoxicitySafeRequired) {
                    bioScores.add(if (props.cytotoxicitySafe == true) 100.0f else if (props.cytotoxicitySafe == false) 20.0f else MISSING_DATA_SCORE_PENALTY)
                }
                if (reqB.hemocompatibleRequired) {
                    bioScores.add(if (props.hemocompatible == true) 100.0f else if (props.hemocompatible == false) 20.0f else MISSING_DATA_SCORE_PENALTY)
                }
                if (reqB.antimicrobialRequired) {
                    bioScores.add(if (props.antimicrobial == true) 100.0f else if (props.antimicrobial == false) 20.0f else MISSING_DATA_SCORE_PENALTY)
                }
                if (reqB.lowEndotoxinRequired) {
                    bioScores.add(if (props.endotoxinConcern != null && props.endotoxinConcern.equals("low", ignoreCase = true)) 100.0f else if (props.endotoxinConcern != null) 20.0f else MISSING_DATA_SCORE_PENALTY)
                }

                sm.scores["biocompatibility"] = if (bioScores.isNotEmpty()) bioScores.average().toFloat() else MISSING_DATA_SCORE_PENALTY
            }

            if (activeWeights.containsKey("cost")) {
                sm.scores["cost"] = scoreOrdinalBand(props.costBand, reqC.maxCostBand, higherIsBetter = false)
            }
            if (activeWeights.containsKey("availability")) {
                sm.scores["availability"] = scoreOrdinalBand(props.availabilityBand, reqC.minAvailabilityBand, higherIsBetter = true)
            }

            // ── PHASE 3: Weighted Aggregation ──
            var totalWeighted = 0f
            var totalWeight = 0f

            for ((dim, weight) in activeWeights) {
                val score = sm.scores[dim]
                if (score != null) {
                    totalWeighted += weight * score
                    totalWeight += weight
                    if (score == MISSING_DATA_SCORE_PENALTY) {
                        sm.missingDimensions.add(dim)
                    }
                }
            }

            val rawScore = if (totalWeight > 0f) (totalWeighted / totalWeight).coerceIn(0f, 100f) else 0f
            sm.totalScore = rawScore

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
                    val isMissing = sm.missingDimensions.contains(dim)
                    FactorContribution(
                        factor = dim,
                        score = score!!,
                        description = describeFactor(dim, score, isMissing = isMissing)
                    )
                }
                .sortedByDescending { it.score }

            val topFactors = contributions.filter { it.score >= 70.0f }.take(5)
            val concerns = contributions.filter { it.score < 50.0f && !sm.missingDimensions.contains(it.factor) }.take(3)
            val tradeoffs = generateTradeoffs(sm)

            Recommendation(
                materialId = sm.material.id,
                materialName = sm.material.name,
                category = sm.material.category,
                score = sm.totalScore,
                confidence = sm.confidence,
                topFactors = topFactors,
                concerns = concerns,
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

    // ── Helper Continuous Scoring Functions (0.0f to 100.0f) ──

    private fun scoreMinRequirement(actualVal: Float?, targetMin: Float?): Float {
        if (targetMin == null || targetMin <= 0f) return 100.0f
        if (actualVal == null) return MISSING_DATA_SCORE_PENALTY

        return if (actualVal < targetMin) {
            val ratio = max(0.0f, actualVal / targetMin)
            max(0.0f, 70.0f * ratio)
        } else {
            val surplus = (actualVal - targetMin) / targetMin
            min(100.0f, 80.0f + 20.0f * min(1.0f, surplus))
        }
    }

    private fun scoreMaxRequirement(actualVal: Float?, targetMax: Float?): Float {
        if (targetMax == null || targetMax <= 0f) return 100.0f
        if (actualVal == null) return MISSING_DATA_SCORE_PENALTY

        return if (actualVal <= targetMax) {
            val margin = (targetMax - actualVal) / targetMax
            min(100.0f, 85.0f + 15.0f * min(1.0f, margin))
        } else {
            val ratio = targetMax / actualVal
            max(0.0f, 85.0f * ratio)
        }
    }

    private fun scoreRangeRequirement(
        actualMin: Float?, actualMax: Float?,
        targetMin: Float?, targetMax: Float?
    ): Float {
        if (targetMin == null && targetMax == null) return 100.0f

        if (targetMin != null && targetMax == null) {
            val actVal = actualMax ?: actualMin
            return scoreMinRequirement(actVal, targetMin)
        }
        if (targetMax != null && targetMin == null) {
            val actVal = actualMin ?: actualMax
            return scoreMaxRequirement(actVal, targetMax)
        }

        if (actualMin == null && actualMax == null) return MISSING_DATA_SCORE_PENALTY
        if (targetMax!! <= targetMin!!) return 100.0f

        val actMin = actualMin ?: actualMax
        val actMax = actualMax ?: actualMin
        if (actMin == null || actMax == null) return MISSING_DATA_SCORE_PENALTY

        val targetMid = (targetMin + targetMax) / 2.0f
        val targetHalf = (targetMax - targetMin) / 2.0f
        val actMid = (actMin + actMax) / 2.0f

        val diff = abs(actMid - targetMid)
        return if (diff <= targetHalf) {
            val ratio = if (targetHalf > 0f) diff / targetHalf else 0f
            100.0f - 15.0f * ratio
        } else {
            val gap = diff - targetHalf
            val span = if (targetHalf > 0f) targetHalf else if (targetMid > 0f) targetMid else 1.0f
            max(0.0f, 85.0f - 70.0f * (gap / span))
        }
    }

    private fun scoreInversePoint(actualValue: Float?, targetMax: Float?): Float {
        return scoreMaxRequirement(actualValue, targetMax)
    }

    private fun scoreOrdinalBand(
        actualBand: String?,
        targetBand: String?,
        higherIsBetter: Boolean = false
    ): Float {
        if (targetBand == null) return 100.0f
        if (actualBand == null) return MISSING_DATA_SCORE_PENALTY

        val bandOrder = mapOf("low" to 1, "med" to 2, "high" to 3)
        val actual = bandOrder[actualBand.lowercase()] ?: 2
        val target = bandOrder[targetBand.lowercase()] ?: 3

        return if (higherIsBetter) {
            when {
                actual > target -> 100.0f
                actual == target -> 85.0f
                target - actual == 1 -> 45.0f
                else -> 15.0f
            }
        } else {
            when {
                actual < target -> 100.0f
                actual == target -> 85.0f
                actual - target == 1 -> 45.0f
                else -> 15.0f
            }
        }
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

    private fun describeFactor(dim: String, score: Float, isMissing: Boolean = false): String {
        val label = factorLabels[dim] ?: dim.replace("_", " ").replaceFirstChar { it.uppercase() }
        if (isMissing) {
            return "$label: Data missing for requested requirement (25% penalty)"
        }
        return when {
            score >= 90.0f -> "$label: Excellent match with target requirements (${score.toInt()}%)"
            score >= 80.0f -> "$label: Very good match, meets requirements comfortably (${score.toInt()}%)"
            score >= 70.0f -> "$label: Good match, within acceptable range (${score.toInt()}%)"
            score >= 50.0f -> "$label: Moderate match, minor deviation from target (${score.toInt()}%)"
            score >= 30.0f -> "$label: Weak match, noticeable gap from requirements (${score.toInt()}%)"
            else -> "$label: Poor match, significant gap from requirements (${score.toInt()}%)"
        }
    }

    private fun generateTradeoffs(sm: ScoredMaterial): List<String> {
        val tradeoffs = mutableListOf<String>()
        val scores = sm.scores

        if (sm.missingDimensions.isNotEmpty()) {
            val missingNames = sm.missingDimensions.map { factorLabels[it] ?: it }
            tradeoffs.add("⚠ Missing data for requested properties: ${missingNames.joinToString(", ")} (25% penalty applied)")
        }

        val mechAvg = listOfNotNull(scores["tensile_strength"], scores["elastic_modulus"])
            .takeIf { it.isNotEmpty() }?.average()?.toFloat()
        val barrierAvg = listOfNotNull(scores["wvtr"], scores["otr"])
            .takeIf { it.isNotEmpty() }?.average()?.toFloat()

        if (mechAvg != null && barrierAvg != null) {
            if (mechAvg > 70.0f && barrierAvg < 50.0f)
                tradeoffs.add("Strong mechanical properties but weak barrier performance — consider blending or coating")
            else if (barrierAvg > 70.0f && mechAvg < 50.0f)
                tradeoffs.add("Good barrier properties but limited mechanical strength — consider reinforcement")
        }

        if (sm.material.evidenceLevel == "low")
            tradeoffs.add("⚠ Evidence level is LOW — properties based on limited or synthetic data")

        val costScore = scores["cost"]
        if (costScore != null && costScore < 50.0f && sm.totalScore > 70.0f)
            tradeoffs.add("High-performing material but cost may be prohibitive — evaluate cost-benefit")

        return tradeoffs
    }

    private class ScoredMaterial(val material: Material) {
        val scores = mutableMapOf<String, Float?>()
        val missingDimensions = mutableListOf<String>()
        val hardFailures = mutableListOf<String>()
        var totalScore: Float = 0f
        var confidence: Float = 0f

        fun addFailure(msg: String) { hardFailures.add(msg) }
    }
}
