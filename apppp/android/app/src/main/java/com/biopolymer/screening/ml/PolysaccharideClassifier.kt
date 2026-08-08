package com.biopolymer.screening.ml

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

/**
 * PolysaccharideClassifier
 *
 * Loads the TFLite model from assets and exposes classify() for on-device inference.
 *
 * Assets required (copy from PolysaccharideProject/app_assets/):
 *  - trained_model.tflite
 *  - feature_columns.json
 *  - label_classes.json
 *  - scaler_params.json
 */
@Deprecated("Scheduled for migration to backend API in v2. Preserved during v1 migration.")
class PolysaccharideClassifier(private val context: Context) {

    private var interpreter: Interpreter? = null
    private var featureColumns: List<String> = emptyList()
    private var labelClasses: List<String> = emptyList()
    private var scalerMean: FloatArray = FloatArray(0)
    private var scalerScale: FloatArray = FloatArray(0)
    private val featureMedians: MutableMap<String, Float> = mutableMapOf()
    private val featureCategories: MutableMap<String, List<String>> = mutableMapOf()

    data class ClassificationResult(
        val predictedClass: String,
        val confidence: Float,
        val allProbabilities: Map<String, Float>
    )

    companion object {
        private const val TAG = "PolysaccharideClassifier"
        private const val MODEL_FILE    = "trained_model.tflite"
        private const val FEATURES_FILE = "feature_columns.json"
        private const val LABELS_FILE   = "label_classes.json"
        private const val PREPROCESS_FILE = "android_preprocessing.json"
    }

    // ─── Initialization ──────────────────────────────────────────────────────

    fun initialize(): Boolean {
        return try {
            // Load model
            val modelBuffer = loadModelFile(MODEL_FILE)
            val options = Interpreter.Options().apply {
                numThreads = 4
                useNNAPI = false
            }
            interpreter = Interpreter(modelBuffer, options)

            // Load feature columns
            val featuresJson = loadAssetAsString(FEATURES_FILE)
            val featArr = JSONArray(featuresJson)
            featureColumns = (0 until featArr.length()).map { featArr.getString(it) }

            // Load label classes
            val labelsJson = loadAssetAsString(LABELS_FILE)
            val labArr = JSONArray(labelsJson)
            labelClasses = (0 until labArr.length()).map { labArr.getString(it) }

            // Load preprocessing parameters
            val prepJson   = JSONObject(loadAssetAsString(PREPROCESS_FILE))
            val meanArr    = prepJson.getJSONArray("scaler_mean")
            val scaleArr   = prepJson.getJSONArray("scaler_scale")
            scalerMean  = FloatArray(meanArr.length()) { meanArr.getDouble(it).toFloat() }
            scalerScale = FloatArray(scaleArr.length()) { scaleArr.getDouble(it).toFloat() }

            val meds = prepJson.getJSONObject("medians")
            val medKeys = meds.keys()
            while (medKeys.hasNext()) {
                val k = medKeys.next()
                featureMedians[k] = meds.getDouble(k).toFloat()
            }

            val cats = prepJson.getJSONObject("categories")
            val catKeys = cats.keys()
            while (catKeys.hasNext()) {
                val k = catKeys.next()
                val arr = cats.getJSONArray(k)
                val list = (0 until arr.length()).map { arr.getString(it) }
                featureCategories[k] = list
            }

            Log.d(TAG, "Initialized: ${featureColumns.size} features, ${labelClasses.size} classes")
            true
        } catch (e: Exception) {
            Log.e(TAG, "Initialization failed: ${e.message}", e)
            false
        }
    }

    // ─── Inference ───────────────────────────────────────────────────────────

    /**
     * Classify a polysaccharide given a map of feature_name → value.
     * Numeric values should be Doubles/Floats; string values are hashed to floats.
     * Returns null if the classifier is not initialized.
     */
    fun classify(features: Map<String, Any>): ClassificationResult? {
        val interp = interpreter ?: run {
            Log.e(TAG, "Interpreter not initialized. Call initialize() first.")
            return null
        }

        // Build float array in feature column order
        val inputArray = FloatArray(featureColumns.size)
        for ((i, col) in featureColumns.withIndex()) {
            val v = features[col]
            inputArray[i] = if (featureCategories.containsKey(col)) {
                // Categorical mapping via saved preprocessor ordinal encoding
                val strVal = v?.toString() ?: "Unknown"
                val idx = featureCategories[col]?.indexOf(strVal) ?: -1
                if (idx >= 0) idx.toFloat() else -1f
            } else {
                // Numeric direct passage + median imputation
                if (v is Number) v.toFloat() else (featureMedians[col] ?: 0f)
            }
        }

        // Apply StandardScaler normalization
        val scaledInput = FloatArray(inputArray.size) { i ->
            val sc = if (i < scalerScale.size && scalerScale[i] != 0f) scalerScale[i] else 1f
            val mn = if (i < scalerMean.size) scalerMean[i] else 0f
            (inputArray[i] - mn) / sc
        }

        // Run inference
        val input  = Array(1) { scaledInput }
        val output = Array(1) { FloatArray(labelClasses.size) }
        interp.run(input, output)

        val probabilities = output[0]
        val maxIdx        = probabilities.indices.maxByOrNull { probabilities[it] } ?: 0
        val maxConf       = probabilities[maxIdx]
        val label         = labelClasses.getOrElse(maxIdx) { "Unknown" }

        val allProbs = labelClasses.mapIndexed { i, cls ->
            cls to (probabilities.getOrElse(i) { 0f })
        }.toMap()

        return ClassificationResult(
            predictedClass    = label,
            confidence        = maxConf,
            allProbabilities  = allProbs
        )
    }

    /**
     * Convenience method to classify using a structured data object.
     * Pass the same fields from master_dataset.json records.
     */
    fun classifyPolysaccharide(
        molecularWeightKda: Double = 0.0,
        solubility: String = "Unknown",
        bondType: String = "Unknown",
        source: String = "Unknown",
        monomerUnit: String = "Unknown"
    ): ClassificationResult? {
        val features = mapOf(
            "molecular_weight_kda" to molecularWeightKda,
            "solubility"           to solubility,
            "bond_type"            to bondType,
            "source"               to source,
            "monomer_unit"         to monomerUnit
        )
        return classify(features)
    }

    // ─── Clean up ────────────────────────────────────────────────────────────

    fun close() {
        interpreter?.close()
        interpreter = null
    }

    // ─── Private helpers ─────────────────────────────────────────────────────

    private fun loadModelFile(filename: String): MappedByteBuffer {
        val assetFd = context.assets.openFd(filename)
        val inputStream = FileInputStream(assetFd.fileDescriptor)
        val channel = inputStream.channel
        return channel.map(FileChannel.MapMode.READ_ONLY, assetFd.startOffset, assetFd.declaredLength)
    }

    private fun loadAssetAsString(filename: String): String {
        return context.assets.open(filename).bufferedReader().use { it.readText() }
    }

}
