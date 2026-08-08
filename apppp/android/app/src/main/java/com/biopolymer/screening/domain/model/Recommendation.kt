package com.biopolymer.screening.domain.model

/**
 * A scored recommendation result for a single material.
 */
data class Recommendation(
    val materialId: String,
    val materialName: String,
    val category: String,
    val score: Float,
    val confidence: Float,
    val topFactors: List<FactorContribution> = emptyList(),
    val concerns: List<FactorContribution> = emptyList(),
    val unmetConstraints: List<String> = emptyList(),
    val tradeoffs: List<String> = emptyList(),
)

data class FactorContribution(
    val factor: String,
    val score: Float,
    val description: String,
)
