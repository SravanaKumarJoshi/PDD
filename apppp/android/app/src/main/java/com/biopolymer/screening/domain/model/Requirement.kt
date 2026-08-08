package com.biopolymer.screening.domain.model

/**
 * User's requirement specification for biopolymer screening.
 * Each section has optional target values and a weight (priority).
 */
data class Requirement(
    val mechanical: MechanicalReq = MechanicalReq(),
    val barrier: BarrierReq = BarrierReq(),
    val biological: BiologicalReq = BiologicalReq(),
    val degradation: DegradationReq = DegradationReq(),
    val processing: ProcessingReq = ProcessingReq(),
    val sterilization: SterilizationReq = SterilizationReq(),
    val sustainability: SustainabilityReq = SustainabilityReq(),
    val cost: CostReq = CostReq(),
)

data class MechanicalReq(
    val tensileStrengthMin: Float? = null,
    val tensileStrengthMax: Float? = null,
    val elasticModulusMin: Float? = null,
    val elasticModulusMax: Float? = null,
    val elongationMin: Float? = null,
    val elongationMax: Float? = null,
    val punctureResistanceMin: Float? = null,
    val weight: Float = 1.0f,
)

data class BarrierReq(
    val wvtrMax: Float? = null,
    val otrMax: Float? = null,
    val weight: Float = 1.0f,
)

data class BiologicalReq(
    val cytotoxicitySafeRequired: Boolean = false,
    val hemocompatibleRequired: Boolean = false,
    val antimicrobialRequired: Boolean = false,
    val lowEndotoxinRequired: Boolean = false,
    val weight: Float = 1.2f,
)

data class DegradationReq(
    val degradationDaysMin: Int? = null,
    val degradationDaysMax: Int? = null,
    val enzymaticRequired: Boolean = false,
    val hydrolyticStabilityMin: String? = null,
    val weight: Float = 1.0f,
)

data class ProcessingReq(
    val filmRequired: Boolean = false,
    val castingRequired: Boolean = false,
    val extrusionRequired: Boolean = false,
    val coatingRequired: Boolean = false,
    val meltRequired: Boolean = false,
    val weight: Float = 0.8f,
)

data class SterilizationReq(
    val gammaRequired: Boolean = false,
    val etoRequired: Boolean = false,
    val steamRequired: Boolean = false,
    val uvRequired: Boolean = false,
    val autoclaveRequired: Boolean = false,
    val weight: Float = 1.0f,
)

data class SustainabilityReq(
    val renewableRequired: Boolean = false,
    val compostableRequired: Boolean = false,
    val weight: Float = 0.6f,
)

data class CostReq(
    val maxCostBand: String? = null,
    val minAvailabilityBand: String? = null,
    val weight: Float = 0.4f,
)
