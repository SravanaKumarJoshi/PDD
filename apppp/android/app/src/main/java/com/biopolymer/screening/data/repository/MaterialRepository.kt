package com.biopolymer.screening.data.repository

import android.content.Context
import android.util.Log
import com.biopolymer.screening.data.local.UserPreferencesRepository
import com.biopolymer.screening.data.local.dao.MaterialCardProjection
import com.biopolymer.screening.data.local.dao.MaterialDao
import com.biopolymer.screening.data.local.dao.MaterialWithProperties
import com.biopolymer.screening.data.local.entity.MaterialEntity
import com.biopolymer.screening.data.local.entity.MaterialPropertyEntity
import com.biopolymer.screening.domain.model.Material
import com.biopolymer.screening.domain.model.MaterialCardModel
import com.biopolymer.screening.domain.model.MaterialProperties
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.roundToInt

private const val TAG = "MaterialRepository"

@Singleton
class MaterialRepository @Inject constructor(
    private val materialDao: MaterialDao,
    private val userPreferencesRepository: UserPreferencesRepository,
    @ApplicationContext private val context: Context,
) {
    private val repositoryScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    init {
        repositoryScope.launch {
            ensureSeeded()
        }
    }

    suspend fun ensureSeeded() = withContext(Dispatchers.IO) {
        val prefs = userPreferencesRepository.userPreferencesFlow.first()
        if (prefs.catalogSeeded) {
            // Resilient fast path: verify DB is actually populated before skipping
            if (materialDao.getMaterialCount() > 0) {
                return@withContext
            }
        } else {
            if (materialDao.getMaterialCount() > 0) {
                userPreferencesRepository.setCatalogSeeded(true)
                return@withContext
            }
        }

        try {
            Log.d(TAG, "Seeding Room database from offline_catalog_50.json on Dispatchers.IO...")
            val jsonString = context.assets.open("offline_catalog_50.json").bufferedReader().use { it.readText() }
            val jsonArray = JSONArray(jsonString)
            val materials = ArrayList<MaterialEntity>(jsonArray.length())
            val properties = ArrayList<MaterialPropertyEntity>(jsonArray.length())

            for (i in 0 until jsonArray.length()) {
                val obj = jsonArray.getJSONObject(i)
                val id = obj.optString("id", "mat-$i")
                val name = obj.optString("name", "Unknown Material")
                val category = obj.optString("category", "unassigned")
                val source = obj.optStringOrNull("source")
                val notes = obj.optStringOrNull("notes")
                val evidenceLevel = obj.optString("evidenceLevel", "high")

                val matEntity = MaterialEntity(
                    id = id,
                    name = name,
                    category = category,
                    source = source,
                    notes = notes,
                    evidenceLevel = evidenceLevel,
                )

                val propEntity = MaterialPropertyEntity(
                    id = "prop-$id",
                    materialId = id,
                    tensileStrengthMpaMin = obj.optFloatOrNull("tensileStrengthMpaMin"),
                    tensileStrengthMpaMax = obj.optFloatOrNull("tensileStrengthMpaMax"),
                    elasticModulusGpaMin = obj.optFloatOrNull("elasticModulusGpaMin"),
                    elasticModulusGpaMax = obj.optFloatOrNull("elasticModulusGpaMax"),
                    elongationPctMin = obj.optFloatOrNull("elongationPctMin"),
                    elongationPctMax = obj.optFloatOrNull("elongationPctMax"),
                    punctureResistanceN = obj.optFloatOrNull("punctureResistanceN"),
                    wvtr = obj.optFloatOrNull("wvtr"),
                    otr = obj.optFloatOrNull("otr"),
                    waterSolubility = obj.optBooleanOrNull("waterSolubility"),
                    swellingRatio = obj.optFloatOrNull("swellingRatio"),
                    degradationDaysMin = obj.optFloatOrNull("degradationDaysMin"),
                    degradationDaysMax = obj.optFloatOrNull("degradationDaysMax"),
                    enzymaticDegradability = obj.optBooleanOrNull("enzymaticDegradability"),
                    hydrolyticStability = obj.optStringOrNull("hydrolyticStability"),
                    cytotoxicitySafe = obj.optBooleanOrNull("cytotoxicitySafe"),
                    hemocompatible = obj.optBooleanOrNull("hemocompatible"),
                    antimicrobial = obj.optBooleanOrNull("antimicrobial"),
                    endotoxinConcern = obj.optStringOrNull("endotoxinConcern"),
                    sterGamma = obj.optBoolean("sterGamma", false),
                    sterEto = obj.optBoolean("sterEto", false),
                    sterSteam = obj.optBoolean("sterSteam", false),
                    sterUv = obj.optBoolean("sterUv", false),
                    sterAutoclave = obj.optBoolean("sterAutoclave", false),
                    procFilm = obj.optBoolean("procFilm", false),
                    procCasting = obj.optBoolean("procCasting", false),
                    procExtrusion = obj.optBoolean("procExtrusion", false),
                    procCoating = obj.optBoolean("procCoating", false),
                    procMelt = obj.optBoolean("procMelt", false),
                    solventCompatible = obj.optStringOrNull("solventCompatible"),
                    costBand = obj.optStringOrNull("costBand"),
                    availabilityBand = obj.optStringOrNull("availabilityBand"),
                    dataCompleteness = obj.optDouble("dataCompleteness", 0.9).toFloat()
                )

                materials.add(matEntity)
                properties.add(propEntity)
            }

            materialDao.insertMaterials(materials)
            materialDao.insertProperties(properties)
            userPreferencesRepository.setCatalogSeeded(true)
            Log.d(TAG, "Successfully seeded ${materials.size} biopolymer materials into Room")
        } catch (e: Exception) {
            Log.e(TAG, "Error seeding offline catalog database", e)
        }
    }

    fun getMaterialCards(): Flow<List<MaterialCardModel>> =
        materialDao.getMaterialCards().map { list -> list.map { it.toCardModel() } }

    fun getMaterialCardsByCategory(category: String): Flow<List<MaterialCardModel>> =
        materialDao.getMaterialCardsByCategory(category).map { list -> list.map { it.toCardModel() } }

    fun searchMaterialCards(query: String): Flow<List<MaterialCardModel>> =
        materialDao.searchMaterialCards(query).map { list -> list.map { it.toCardModel() } }

    fun getAllMaterials(): Flow<List<Material>> =
        materialDao.getAllMaterials().map { list -> list.map { it.toDomain() } }

    fun getMaterialsByCategory(category: String): Flow<List<Material>> =
        materialDao.getMaterialsByCategory(category).map { list -> list.map { it.toDomain() } }

    fun searchMaterials(query: String): Flow<List<Material>> =
        materialDao.searchMaterials(query).map { list -> list.map { it.toDomain() } }

    suspend fun getMaterialById(id: String): Material? =
        materialDao.getMaterialById(id)?.toDomain()

    suspend fun getAllMaterialsSync(): List<Material> {
        val materials = materialDao.getAllMaterialsSync().map { it.toDomain() }
        Log.d(TAG, "getAllMaterialsSync: Retrieved ${materials.size} materials")
        return materials
    }

    fun getCategories(): Flow<List<String>> = materialDao.getCategories()

    suspend fun getMaterialCount(): Int = materialDao.getMaterialCount()
}

private fun JSONObject.optFloatOrNull(key: String): Float? =
    if (has(key) && !isNull(key)) getDouble(key).toFloat() else null

private fun JSONObject.optBooleanOrNull(key: String): Boolean? =
    if (has(key) && !isNull(key)) getBoolean(key) else null

private fun JSONObject.optStringOrNull(key: String): String? =
    if (has(key) && !isNull(key)) getString(key) else null



fun MaterialWithProperties.toDomain(): Material {
    val p = properties
    return Material(
        id = material.id,
        name = material.name,
        category = material.category,
        source = material.source,
        notes = material.notes,
        evidenceLevel = material.evidenceLevel,
        properties = MaterialProperties(
            tensileStrengthMin = p?.tensileStrengthMpaMin,
            tensileStrengthMax = p?.tensileStrengthMpaMax,
            elasticModulusMin = p?.elasticModulusGpaMin,
            elasticModulusMax = p?.elasticModulusGpaMax,
            elongationMin = p?.elongationPctMin,
            elongationMax = p?.elongationPctMax,
            punctureResistance = p?.punctureResistanceN,
            wvtr = p?.wvtr,
            otr = p?.otr,
            waterSolubility = p?.waterSolubility,
            swellingRatio = p?.swellingRatio,
            degradationDaysMin = p?.degradationDaysMin?.roundToInt(),
            degradationDaysMax = p?.degradationDaysMax?.roundToInt(),
            enzymaticDegradability = p?.enzymaticDegradability,
            hydrolyticStability = p?.hydrolyticStability,
            cytotoxicitySafe = p?.cytotoxicitySafe,
            hemocompatible = p?.hemocompatible,
            antimicrobial = p?.antimicrobial,
            endotoxinConcern = p?.endotoxinConcern,
            sterGamma = p?.sterGamma ?: false,
            sterEto = p?.sterEto ?: false,
            sterSteam = p?.sterSteam ?: false,
            sterUv = p?.sterUv ?: false,
            sterAutoclave = p?.sterAutoclave ?: false,
            procFilm = p?.procFilm ?: false,
            procCasting = p?.procCasting ?: false,
            procExtrusion = p?.procExtrusion ?: false,
            procCoating = p?.procCoating ?: false,
            procMelt = p?.procMelt ?: false,
            solventCompatible = p?.solventCompatible,
            costBand = p?.costBand,
            availabilityBand = p?.availabilityBand,
            dataCompleteness = p?.dataCompleteness ?: 0f,
        )
    )
}

fun MaterialCardProjection.toCardModel(): MaterialCardModel = MaterialCardModel(
    id = id,
    name = name,
    category = category,
    evidenceLevel = evidenceLevel,
    descriptionText = notes ?: source ?: "Not Available",
    tensileStrengthMin = tensileStrengthMpaMin,
    tensileStrengthMax = tensileStrengthMpaMax,
    degradationDaysMin = degradationDaysMin,
    degradationDaysMax = degradationDaysMax,
    cytotoxicitySafe = cytotoxicitySafe
)
