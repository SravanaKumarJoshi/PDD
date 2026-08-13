package com.biopolymer.screening.data.remote.dto

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ScreeningRequestDto(
    @Json(name = "tensile_strength") val tensileStrength: Double? = null,
    @Json(name = "elastic_modulus") val elasticModulus: Double? = null,
    @Json(name = "elongation_pct") val elongationPct: Double? = null,
    @Json(name = "flexibility") val flexibility: Double? = null,
    @Json(name = "wvtr") val wvtr: Double? = null,
    @Json(name = "oxygen_permeability") val oxygenPermeability: Double? = null,
    @Json(name = "min_biocompatibility") val minBiocompatibility: Double? = null,
    @Json(name = "target_biodegradation_days") val targetBiodegradationDays: Double? = null,
    @Json(name = "sterilization_gamma") val sterilizationGamma: Boolean = false,
    @Json(name = "sterilization_eto") val sterilizationEto: Boolean = false,
    @Json(name = "sterilization_steam") val sterilizationSteam: Boolean = false,
    @Json(name = "explainability_method") val explainabilityMethod: String = "shap"
)

@JsonClass(generateAdapter = true)
data class FactorContributionDto(
    @Json(name = "feature") val feature: String,
    @Json(name = "label") val label: String,
    @Json(name = "score") val score: Double,
    @Json(name = "direction") val direction: String
)

@JsonClass(generateAdapter = true)
data class ExplanationDto(
    @Json(name = "method") val method: String,
    @Json(name = "explanation_text") val explanationText: String,
    @Json(name = "top_contributions") val topContributions: List<FactorContributionDto> = emptyList()
)

@JsonClass(generateAdapter = true)
data class RiskCategoryDto(
    @Json(name = "level") val level: String? = "low",
    @Json(name = "label") val label: String = "Low Confidence",
    @Json(name = "color") val color: String = "red",
    @Json(name = "reasons") val reasons: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class ScreeningResultItemDto(
    @Json(name = "material_id") val materialId: String,
    @Json(name = "polymer") val polymer: String,
    @Json(name = "category") val category: String,
    @Json(name = "rank") val rank: Int = 1,
    @Json(name = "final_score") val finalScore: Double,
    @Json(name = "overall_score") val overallScore: Double = finalScore,
    @Json(name = "rule_score") val ruleScore: Double = finalScore,
    @Json(name = "ml_score") val mlScore: Double = finalScore,
    @Json(name = "blend_formula") val blendFormula: String? = null,
    @Json(name = "tie_break_reason") val tieBreakReason: String? = null,
    @Json(name = "ml_probability") val mlProbability: Double,
    @Json(name = "multi_criteria_score") val multiCriteriaScore: Double,
    @Json(name = "confidence") val confidence: Double,
    @Json(name = "risk_category") val riskCategory: RiskCategoryDto? = null,
    @Json(name = "is_pareto_optimal") val isParetoOptimal: Boolean = false,
    @Json(name = "explanation") val explanation: ExplanationDto? = null,
    @Json(name = "score_breakdown") val scoreBreakdown: Map<String, Any?> = emptyMap(),
    @Json(name = "properties") val properties: Map<String, Any?> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class ModelMetadataDto(
    @Json(name = "model_version") val modelVersion: String,
    @Json(name = "algorithm") val algorithm: String,
    @Json(name = "dataset_hash") val datasetHash: String,
    @Json(name = "prediction_timestamp") val predictionTimestamp: String
)

@JsonClass(generateAdapter = true)
data class PerformanceMetricsDto(
    @Json(name = "total_request_duration_ms") val totalRequestDurationMs: Double
)

@JsonClass(generateAdapter = true)
data class ScreeningResponseDto(
    @Json(name = "screening_id") val screeningId: String,
    @Json(name = "model_metadata") val modelMetadata: ModelMetadataDto,
    @Json(name = "performance_metrics") val performanceMetrics: PerformanceMetricsDto? = null,
    @Json(name = "total_evaluated") val totalEvaluated: Int,
    @Json(name = "results") val results: List<ScreeningResultItemDto> = emptyList()
)

@JsonClass(generateAdapter = true)
data class HealthResponseDto(
    @Json(name = "status") val status: String? = null,
    @Json(name = "service") val service: String? = null,
    @Json(name = "version") val version: String? = null,
    @Json(name = "environment") val environment: String? = null,
    @Json(name = "mysql_connected") val mysqlConnected: Boolean = false,
    @Json(name = "uptime_seconds") val uptimeSeconds: Double? = null,
    @Json(name = "server_time") val serverTime: String? = null,
    @Json(name = "request_id") val requestId: String? = null
)

