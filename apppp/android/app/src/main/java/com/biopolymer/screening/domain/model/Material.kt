package com.biopolymer.screening.domain.model

/**
 * Domain model representing a biopolymer material with its properties.
 */
data class Material(
    val id: String,
    val name: String,
    val category: String,
    val source: String? = null,
    val notes: String? = null,
    val evidenceLevel: String = "low",
    val references: List<String> = emptyList(),
    val properties: MaterialProperties = MaterialProperties()
)

data class MaterialProperties(
    // Mechanical
    val tensileStrengthMin: Float? = null,
    val tensileStrengthMax: Float? = null,
    val elasticModulusMin: Float? = null,
    val elasticModulusMax: Float? = null,
    val elongationMin: Float? = null,
    val elongationMax: Float? = null,
    val punctureResistance: Float? = null,

    // Barrier
    val wvtr: Float? = null,
    val otr: Float? = null,

    // Solubility
    val waterSolubility: Boolean? = null,
    val swellingRatio: Float? = null,

    // Degradation
    val degradationDaysMin: Int? = null,
    val degradationDaysMax: Int? = null,
    val enzymaticDegradability: Boolean? = null,
    val hydrolyticStability: String? = null,

    // Biological
    val cytotoxicitySafe: Boolean? = null,
    val hemocompatible: Boolean? = null,
    val antimicrobial: Boolean? = null,
    val endotoxinConcern: String? = null,

    // Sterilization
    val sterGamma: Boolean = false,
    val sterEto: Boolean = false,
    val sterSteam: Boolean = false,
    val sterUv: Boolean = false,
    val sterAutoclave: Boolean = false,

    // Processing
    val procFilm: Boolean = false,
    val procCasting: Boolean = false,
    val procExtrusion: Boolean = false,
    val procCoating: Boolean = false,
    val procMelt: Boolean = false,
    val solventCompatible: String? = null,

    // Cost
    val costBand: String? = null,
    val availabilityBand: String? = null,

    // Meta
    val dataCompleteness: Float = 0f,
)
