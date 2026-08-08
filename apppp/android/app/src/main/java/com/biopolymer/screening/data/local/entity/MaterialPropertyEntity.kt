package com.biopolymer.screening.data.local.entity

import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

/**
 * Room entity for material properties.
 * One-to-one relationship with MaterialEntity.
 */
@Entity(
    tableName = "material_properties",
    foreignKeys = [
        ForeignKey(
            entity = MaterialEntity::class,
            parentColumns = ["id"],
            childColumns = ["materialId"],
            onDelete = ForeignKey.CASCADE
        )
    ],
    indices = [Index("materialId", unique = true)]
)
data class MaterialPropertyEntity(
    @PrimaryKey val id: String,
    val materialId: String,

    // Mechanical
    val tensileStrengthMpaMin: Float? = null,
    val tensileStrengthMpaMax: Float? = null,
    val elasticModulusGpaMin: Float? = null,
    val elasticModulusGpaMax: Float? = null,
    val elongationPctMin: Float? = null,
    val elongationPctMax: Float? = null,
    val punctureResistanceN: Float? = null,

    // Barrier
    val wvtr: Float? = null,
    val otr: Float? = null,

    // Solubility
    val waterSolubility: Boolean? = null,
    val swellingRatio: Float? = null,

    // Degradation
    // Note: stored as FLOAT in MySQL — Float matches the server-side type to
    // prevent fractional day values (e.g. 4.23) from being silently truncated.
    val degradationDaysMin: Float? = null,
    val degradationDaysMax: Float? = null,
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
    val updatedAt: Long = System.currentTimeMillis()
)
