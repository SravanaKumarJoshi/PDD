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
import com.biopolymer.screening.data.remote.ApiService
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
    private val apiService: ApiService,
    @ApplicationContext private val context: Context,
) {
    private val repositoryScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    init {
        repositoryScope.launch {
            ensureSeeded()
            refreshMaterialsFromBackend()
        }
    }

    suspend fun ensureSeeded() = withContext(Dispatchers.IO) {
        val prefs = userPreferencesRepository.userPreferencesFlow.first()
        val currentCount = materialDao.getMaterialCount()
        if (prefs.catalogSeeded && currentCount > 0) {
            return@withContext
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

    suspend fun getMaterialById(id: String): Material? = withContext(Dispatchers.IO) {
        Log.d(TAG, "Selected material ID: '$id'")
        try {
            Log.d(TAG, "Details API request: GET api/v1/materials/$id")
            val resp = apiService.getMaterial(id)
            Log.d(TAG, "HTTP status: ${resp.code()}")
            if (resp.isSuccessful && resp.body() != null) {
                val map = resp.body()!!
                val returnedId = map["id"]?.toString() ?: map["material_id"]?.toString() ?: id
                Log.d(TAG, "Returned material ID: '$returnedId'")
                val domainMaterial = mapDictToMaterial(returnedId, map)
                try {
                    cacheMaterial(domainMaterial)
                } catch (cacheErr: Exception) {
                    Log.w(TAG, "Failed to cache fetched material $returnedId into Room: ${cacheErr.message}")
                }
                return@withContext domainMaterial
            } else {
                Log.w(TAG, "Details API returned non-success status ${resp.code()} for material ID '$id'")
            }
        } catch (netErr: Exception) {
            Log.w(TAG, "Details API call failed for material ID '$id': ${netErr.message}")
        }

        // Fallback to local Room database
        Log.d(TAG, "Falling back to local Room database for material ID '$id'")
        val local = materialDao.getMaterialById(id)?.toDomain()
        if (local != null) {
            Log.d(TAG, "Local Room database returned material ID: '${local.id}'")
        } else {
            Log.w(TAG, "Local Room database also did not find material ID: '$id'")
        }
        local
    }

    private suspend fun cacheMaterial(material: Material) {
        val entity = MaterialEntity(
            id = material.id,
            name = material.name,
            category = material.category,
            source = material.source,
            notes = material.notes,
            evidenceLevel = material.evidenceLevel
        )
        val p = material.properties
        val propEntity = MaterialPropertyEntity(
            id = "prop-${material.id}",
            materialId = material.id,
            tensileStrengthMpaMin = p.tensileStrengthMin,
            tensileStrengthMpaMax = p.tensileStrengthMax,
            elasticModulusGpaMin = p.elasticModulusMin,
            elasticModulusGpaMax = p.elasticModulusMax,
            elongationPctMin = p.elongationMin,
            elongationPctMax = p.elongationMax,
            punctureResistanceN = p.punctureResistance,
            wvtr = p.wvtr,
            otr = p.otr,
            waterSolubility = p.waterSolubility,
            swellingRatio = p.swellingRatio,
            degradationDaysMin = p.degradationDaysMin?.toFloat(),
            degradationDaysMax = p.degradationDaysMax?.toFloat(),
            enzymaticDegradability = p.enzymaticDegradability,
            hydrolyticStability = p.hydrolyticStability,
            cytotoxicitySafe = p.cytotoxicitySafe,
            hemocompatible = p.hemocompatible,
            antimicrobial = p.antimicrobial,
            endotoxinConcern = p.endotoxinConcern,
            sterGamma = p.sterGamma,
            sterEto = p.sterEto,
            sterSteam = p.sterSteam,
            sterUv = p.sterUv,
            sterAutoclave = p.sterAutoclave,
            procFilm = p.procFilm,
            procCasting = p.procCasting,
            procExtrusion = p.procExtrusion,
            procCoating = p.procCoating,
            procMelt = p.procMelt,
            solventCompatible = p.solventCompatible,
            costBand = p.costBand,
            availabilityBand = p.availabilityBand,
            dataCompleteness = p.dataCompleteness
        )
        materialDao.insertMaterials(listOf(entity))
        materialDao.insertProperties(listOf(propEntity))
    }

    private fun mapDictToMaterial(materialId: String, map: Map<String, Any?>): Material {
        val name = map["name"]?.toString() ?: map["polymer"]?.toString() ?: "Unknown Material"
        val category = map["category"]?.toString() ?: "Unassigned"
        val source = map["source"]?.toString()
        val notes = map["notes"]?.toString()
        val evidenceLevel = map["evidence_level"]?.toString() ?: map["evidenceLevel"]?.toString() ?: "medium"

        val ts = (map["tensile_strength"] as? Number)?.toFloat()
            ?: (map["tensile_strength_mpa_min"] as? Number)?.toFloat()
            ?: (map["tensileStrengthMin"] as? Number)?.toFloat()
        val tsMax = (map["tensile_strength_mpa_max"] as? Number)?.toFloat()
            ?: (map["tensileStrengthMax"] as? Number)?.toFloat() ?: ts

        val em = (map["elastic_modulus"] as? Number)?.toFloat()
            ?: (map["elastic_modulus_gpa_min"] as? Number)?.toFloat()
            ?: (map["elasticModulusMin"] as? Number)?.toFloat()
        val emMax = (map["elastic_modulus_gpa_max"] as? Number)?.toFloat()
            ?: (map["elasticModulusMax"] as? Number)?.toFloat() ?: em

        val el = (map["elongation_pct"] as? Number)?.toFloat()
            ?: (map["elongation_pct_min"] as? Number)?.toFloat()
            ?: (map["elongationMin"] as? Number)?.toFloat()
        val elMax = (map["elongation_pct_max"] as? Number)?.toFloat()
            ?: (map["elongationMax"] as? Number)?.toFloat() ?: el

        val wvtr = (map["wvtr"] as? Number)?.toFloat()
        val otr = (map["oxygen_permeability"] as? Number)?.toFloat()
            ?: (map["otr"] as? Number)?.toFloat()

        val bio = (map["biocompatibility"] as? Number)?.toFloat()
        val cytotoxicitySafe = if (bio != null) bio >= 5.0 else (map["cytotoxicity_safe"] as? Boolean ?: (map["cytotoxicitySafe"] as? Boolean))
        val hemocompatible = (map["hemocompatible"] as? Boolean)
        val antimicrobial = (map["antimicrobial"] as? Number)?.toInt() == 1 || (map["antimicrobial"] as? Boolean) == true

        val degradationDays = (map["biodegradation_days"] as? Number)?.toInt()
            ?: (map["degradation_days_min"] as? Number)?.toInt()
            ?: (map["degradationDaysMin"] as? Number)?.toInt()
        val degradationDaysMax = (map["degradation_days_max"] as? Number)?.toInt()
            ?: (map["degradationDaysMax"] as? Number)?.toInt() ?: degradationDays

        val sterGamma = (map["sterilization_gamma"] as? Number)?.toInt() == 1 || (map["ster_gamma"] as? Boolean) == true || (map["sterGamma"] as? Boolean) == true
        val sterEto = (map["sterilization_eto"] as? Number)?.toInt() == 1 || (map["ster_eto"] as? Boolean) == true || (map["sterEto"] as? Boolean) == true
        val sterSteam = (map["sterilization_steam"] as? Number)?.toInt() == 1 || (map["ster_steam"] as? Boolean) == true || (map["sterSteam"] as? Boolean) == true

        val procFilm = (map["film_forming"] as? Number)?.toInt() == 1 || (map["proc_film"] as? Boolean) == true || (map["procFilm"] as? Boolean) == true

        val dataComp = (map["data_completeness"] as? Number)?.toFloat() ?: (map["dataCompleteness"] as? Number)?.toFloat() ?: 0.9f

        return Material(
            id = materialId,
            name = name,
            category = category,
            source = source,
            notes = notes,
            evidenceLevel = evidenceLevel,
            properties = MaterialProperties(
                tensileStrengthMin = ts,
                tensileStrengthMax = tsMax,
                elasticModulusMin = em,
                elasticModulusMax = emMax,
                elongationMin = el,
                elongationMax = elMax,
                punctureResistance = (map["puncture_resistance"] as? Number)?.toFloat(),
                wvtr = wvtr,
                otr = otr,
                waterSolubility = (map["water_solubility"] as? Boolean),
                swellingRatio = (map["swelling_ratio"] as? Number)?.toFloat(),
                degradationDaysMin = degradationDays,
                degradationDaysMax = degradationDaysMax,
                enzymaticDegradability = (map["enzymatic_degradability"] as? Boolean),
                hydrolyticStability = map["hydrolytic_stability"]?.toString(),
                cytotoxicitySafe = cytotoxicitySafe,
                hemocompatible = hemocompatible,
                antimicrobial = antimicrobial,
                endotoxinConcern = map["endotoxin_concern"]?.toString(),
                sterGamma = sterGamma,
                sterEto = sterEto,
                sterSteam = sterSteam,
                sterUv = (map["ster_uv"] as? Boolean) ?: (map["sterUv"] as? Boolean) ?: false,
                sterAutoclave = (map["ster_autoclave"] as? Boolean) ?: (map["sterAutoclave"] as? Boolean) ?: false,
                procFilm = procFilm,
                procCasting = (map["proc_casting"] as? Boolean) ?: (map["procCasting"] as? Boolean) ?: false,
                procExtrusion = (map["proc_extrusion"] as? Boolean) ?: (map["procExtrusion"] as? Boolean) ?: false,
                procCoating = (map["proc_coating"] as? Boolean) ?: (map["procCoating"] as? Boolean) ?: false,
                procMelt = (map["proc_melt"] as? Boolean) ?: (map["procMelt"] as? Boolean) ?: false,
                solventCompatible = map["solvent_compatible"]?.toString(),
                costBand = map["cost_band"]?.toString() ?: map["costBand"]?.toString(),
                availabilityBand = map["availability_band"]?.toString() ?: map["availabilityBand"]?.toString(),
                dataCompleteness = dataComp
            )
        )
    }

    suspend fun getAllMaterialsSync(): List<Material> {
        val materials = materialDao.getAllMaterialsSync().map { it.toDomain() }
        Log.d(TAG, "getAllMaterialsSync: Retrieved ${materials.size} materials")
        return materials
    }

    fun getCategories(): Flow<List<String>> = materialDao.getCategories()

    suspend fun getMaterialCount(): Int = materialDao.getMaterialCount()

    suspend fun clearLocalCatalog() = withContext(Dispatchers.IO) {
        materialDao.deleteAllMaterials()
        userPreferencesRepository.setCatalogSeeded(false)
        Log.d(TAG, "Cleared local Room catalog database cache.")
    }

    suspend fun refreshMaterialsFromBackend(): Result<Int> = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "refreshMaterialsFromBackend: Fetching materials from FastAPI backend API")
            val resp = apiService.getMaterials()
            if (!resp.isSuccessful || resp.body() == null) {
                val err = "Backend HTTP ${resp.code()}"
                Log.w(TAG, "refreshMaterialsFromBackend failed: $err")
                return@withContext Result.failure(Exception(err))
            }

            val remoteItems = resp.body()!!
            if (remoteItems.isEmpty()) {
                Log.d(TAG, "refreshMaterialsFromBackend: 0 items returned")
                return@withContext Result.success(0)
            }

            val materials = ArrayList<MaterialEntity>(remoteItems.size)
            val properties = ArrayList<MaterialPropertyEntity>(remoteItems.size)

            for ((idx, map) in remoteItems.withIndex()) {
                val id = map["id"]?.toString() ?: map["material_id"]?.toString() ?: "mat-$idx"
                val name = map["name"]?.toString() ?: map["polymer"]?.toString() ?: "Unknown Material"
                val category = map["category"]?.toString() ?: "Unassigned"
                val source = map["source"]?.toString()
                val notes = map["notes"]?.toString()
                val evidenceLevel = map["evidence_level"]?.toString() ?: map["evidenceLevel"]?.toString() ?: "medium"

                materials.add(
                    MaterialEntity(
                        id = id,
                        name = name,
                        category = category,
                        source = source,
                        notes = notes,
                        evidenceLevel = evidenceLevel,
                    )
                )

                val ts = (map["tensile_strength"] as? Number)?.toFloat()
                    ?: (map["tensile_strength_mpa_min"] as? Number)?.toFloat()
                val em = (map["elastic_modulus"] as? Number)?.toFloat()
                    ?: (map["elastic_modulus_gpa_min"] as? Number)?.toFloat()
                val el = (map["elongation_pct"] as? Number)?.toFloat()
                    ?: (map["elongation_pct_min"] as? Number)?.toFloat()
                val wvtr = (map["wvtr"] as? Number)?.toFloat()
                val otr = (map["oxygen_permeability"] as? Number)?.toFloat() ?: (map["otr"] as? Number)?.toFloat()
                val bio = (map["biocompatibility"] as? Number)?.toFloat()
                val cytotoxicitySafe = if (bio != null) bio >= 5.0 else (map["cytotoxicity_safe"] as? Boolean)
                val degradationDays = (map["biodegradation_days"] as? Number)?.toFloat()
                    ?: (map["degradation_days_min"] as? Number)?.toFloat()

                properties.add(
                    MaterialPropertyEntity(
                        id = "prop-$id",
                        materialId = id,
                        tensileStrengthMpaMin = ts,
                        tensileStrengthMpaMax = ts,
                        elasticModulusGpaMin = em,
                        elasticModulusGpaMax = em,
                        elongationPctMin = el,
                        elongationPctMax = el,
                        punctureResistanceN = null,
                        wvtr = wvtr,
                        otr = otr,
                        waterSolubility = null,
                        swellingRatio = null,
                        degradationDaysMin = degradationDays,
                        degradationDaysMax = degradationDays,
                        enzymaticDegradability = null,
                        hydrolyticStability = null,
                        cytotoxicitySafe = cytotoxicitySafe,
                        hemocompatible = null,
                        antimicrobial = null,
                        endotoxinConcern = null,
                        sterGamma = (map["sterilization_gamma"] as? Number)?.toInt() == 1,
                        sterEto = (map["sterilization_eto"] as? Number)?.toInt() == 1,
                        sterSteam = (map["sterilization_steam"] as? Number)?.toInt() == 1,
                        sterUv = false,
                        sterAutoclave = false,
                        procFilm = (map["film_forming"] as? Number)?.toInt() == 1,
                        procCasting = false,
                        procExtrusion = false,
                        procCoating = false,
                        procMelt = false,
                        solventCompatible = null,
                        costBand = null,
                        availabilityBand = null,
                        dataCompleteness = 0.9f
                    )
                )
            }

            materialDao.insertMaterials(materials)
            materialDao.insertProperties(properties)
            userPreferencesRepository.setCatalogSeeded(true)
            Log.d(TAG, "refreshMaterialsFromBackend: Successfully synced ${materials.size} materials from backend database")
            Result.success(materials.size)
        } catch (e: Exception) {
            Log.e(TAG, "refreshMaterialsFromBackend error: ${e.message}", e)
            Result.failure(e)
        }
    }
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
