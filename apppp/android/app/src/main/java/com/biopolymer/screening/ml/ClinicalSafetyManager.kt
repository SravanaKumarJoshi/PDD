package com.biopolymer.screening.ml

import android.content.Context
import android.util.Log
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

/**
 * ClinicalSafetyManager
 * =====================
 * Manages clinical safety gating for the Polysaccharide app.
 */
enum class AppMode { DEMO, CLINICAL }

data class ClinicalGateResult(
    val canShowPrediction: Boolean,
    val reason: String,
    val modelVersion: String,
    val clinicalModelValid: Boolean,
    val taxonomyModelValid: Boolean,
    val confidenceThreshold: Float,
    val mode: AppMode
)

object ClinicalSafetyManager {

    private const val TAG = "ClinicalSafetyManager"
    private const val MANIFEST_ASSET = "model_manifest.json"
    private const val AUDIT_LOG_FILENAME = "inference_audit_log.jsonl"

    var currentMode: AppMode = AppMode.DEMO
        private set

    private var manifest: JSONObject? = null
    private var isInitialized = false

    fun initialize(context: Context) {
        if (isInitialized) return
        try {
            val json = context.assets.open(MANIFEST_ASSET).bufferedReader().readText()
            manifest = JSONObject(json)
            isInitialized = true
        } catch (e: Exception) {
            Log.e(TAG, "Failed to load model manifest: ${e.message}")
            manifest = null
        }
    }

    fun setMode(mode: AppMode) {
        currentMode = mode
    }

    fun isModelValidForClinical(): Boolean {
        return manifest?.optBoolean("clinical_model_valid", false) ?: false
    }

    fun isPredictionsEnabledInClinicianMode(): Boolean {
        return manifest?.optBoolean("predictions_enabled_in_clinician_mode", false) ?: false
    }

    fun isTaxonomyModelValid(): Boolean {
        return manifest?.optBoolean("taxonomy_model_valid", false) ?: false
    }

    fun getModelVersion(): String = manifest?.optString("model_version", "unknown") ?: "unknown"

    fun getConfidenceThreshold(): Float =
        manifest?.optDouble("confidence_threshold", 0.75)?.toFloat() ?: 0.75f

    fun shouldShowPrediction(confidence: Float): ClinicalGateResult {
        val threshold = getConfidenceThreshold()
        val clinicalValid = isModelValidForClinical()
        val predictionsEnabled = isPredictionsEnabledInClinicianMode()
        val taxonomyValid = isTaxonomyModelValid()
        val version = getModelVersion()

        return when (currentMode) {
            AppMode.DEMO -> {
                val canShow = confidence >= threshold
                ClinicalGateResult(
                    canShowPrediction = canShow,
                    reason = if (canShow) "Reference classification output (not clinical decision support)." else "Confidence below threshold",
                    modelVersion = version,
                    clinicalModelValid = clinicalValid,
                    taxonomyModelValid = taxonomyValid,
                    confidenceThreshold = threshold,
                    mode = AppMode.DEMO
                )
            }
            AppMode.CLINICAL -> {
                // STRICT GATING: Check BOTH clinical_model_valid AND predictions_enabled_in_clinician_mode
                val canShow = clinicalValid && predictionsEnabled && confidence >= threshold
                
                ClinicalGateResult(
                    canShowPrediction = canShow,
                    reason = if (canShow) "Reference classification output (not clinical decision support)."
                            else "Knowledge Base Only: ML predictions are currently disabled due to a lack of independent clinical validation.",
                    modelVersion = version,
                    clinicalModelValid = clinicalValid,
                    taxonomyModelValid = taxonomyValid,
                    confidenceThreshold = threshold,
                    mode = AppMode.CLINICAL
                )
            }
        }
    }

    fun logInference(context: Context, outputLabel: String, confidence: Float, gateResult: ClinicalGateResult) {
        // Logging logic...
    }
}
