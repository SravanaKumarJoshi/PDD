package com.biopolymer.screening.domain.model

import androidx.compose.runtime.Immutable

/**
 * Lightweight, immutable domain model for catalog list cards.
 * Avoids loading and deserializing all ~40+ full material properties during list rendering.
 */
@Immutable
data class MaterialCardModel(
    val id: String,
    val name: String,
    val category: String,
    val evidenceLevel: String = "low",
    val descriptionText: String = "Not Available",
    val tensileStrengthMin: Float? = null,
    val tensileStrengthMax: Float? = null,
    val degradationDaysMin: Float? = null,
    val degradationDaysMax: Float? = null,
    val cytotoxicitySafe: Boolean? = null,
)
