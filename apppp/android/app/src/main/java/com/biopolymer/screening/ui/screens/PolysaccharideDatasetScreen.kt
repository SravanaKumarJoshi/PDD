package com.biopolymer.screening.ui.screens

import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.expandVertically
import androidx.compose.animation.shrinkVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.biopolymer.screening.ml.ClinicalSafetyManager
import com.biopolymer.screening.ml.PolysaccharideClassifier
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.roundToInt

// ─── Data model ──────────────────────────────────────────────────────────────

data class PolysaccharideEntry(
    val name: String,
    val category: String,
    val source: String,
    val monomerUnit: String,
    val bondType: String,
    val molecularWeightKda: Double,
    val solubility: String,
    val biologicalFunction: String,
    val medicalApplication: String,
    val foodApplication: String,
    val rawJson: JSONObject,
)

fun JSONObject.getStrOrDefault(key: String) = optString(key, "—").ifBlank { "—" }
fun JSONObject.getDblOrZero(key: String)    = optDouble(key, 0.0)

fun parsePolysaccharideEntry(obj: JSONObject): PolysaccharideEntry {
    val name = obj.getStrOrDefault("name")
    val cat  = obj.getStrOrDefault("category").ifBlank {
        obj.getStrOrDefault("carbohydrate_class") }
    return PolysaccharideEntry(
        name                = name,
        category            = cat,
        source              = obj.getStrOrDefault("source").ifBlank { obj.getStrOrDefault("source_organism") },
        monomerUnit         = obj.getStrOrDefault("monomer_unit").ifBlank { obj.getStrOrDefault("primary_monomer") },
        bondType            = obj.getStrOrDefault("bond_type").ifBlank { obj.getStrOrDefault("glycosidic_linkage") },
        molecularWeightKda  = obj.getDblOrZero("molecular_weight_kda"),
        solubility          = obj.getStrOrDefault("solubility"),
        biologicalFunction  = obj.getStrOrDefault("biological_function"),
        medicalApplication  = obj.getStrOrDefault("medical_application"),
        foodApplication     = obj.getStrOrDefault("food_application"),
        rawJson             = obj,
    )
}

fun loadKnowledgeBase(context: Context): List<PolysaccharideEntry> {
    return try {
        val fileName = "polysaccharide_knowledge_base.json"
        val raw = context.assets.open(fileName).bufferedReader().use { it.readText() }
        val value = org.json.JSONTokener(raw).nextValue()
        val arr = if (value is JSONObject) value.getJSONArray("entries") else value as JSONArray
        (0 until arr.length()).map { parsePolysaccharideEntry(arr.getJSONObject(it)) }
    } catch (e: Exception) {
        android.util.Log.e("Dataset", "Failed to load knowledge base", e)
        emptyList()
    }
}

// ─── Main Screen ─────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PolysaccharideDatasetScreen() {
    val context = LocalContext.current
    var searchQuery   by remember { mutableStateOf("") }
    var selectedCat   by remember { mutableStateOf("All") }
    var classifierResult by remember { mutableStateOf<String?>(null) }
    var classifierReason by remember { mutableStateOf<String?>(null) }
    var isClassifying by remember { mutableStateOf(false) }
    var showClassifier by remember { mutableStateOf(false) }

    val allEntries = remember { loadKnowledgeBase(context) }
    val classifier = remember { PolysaccharideClassifier(context) }
    
    LaunchedEffect(Unit) { 
        ClinicalSafetyManager.initialize(context)
        classifier.initialize() 
    }

    if (allEntries.isEmpty()) {
        Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Knowledge base unavailable. Re-run asset copy script.", 
                 color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.Bold)
        }
        return
    }

    val categories = remember(allEntries) {
        listOf("All") + allEntries.map { it.category }.distinct().sorted()
    }

    val filtered = remember(allEntries, searchQuery, selectedCat) {
        allEntries.filter { entry ->
            val matchSearch = entry.name.contains(searchQuery, ignoreCase = true) || 
                             entry.category.contains(searchQuery, ignoreCase = true)
            val matchCat = selectedCat == "All" || entry.category == selectedCat
            matchSearch && matchCat
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Polysaccharide Database", fontWeight = FontWeight.Bold) },
                actions = {
                    IconButton(onClick = { showClassifier = !showClassifier }) {
                        Icon(Icons.Default.Science, contentDescription = "ML Classifier")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.primaryContainer)
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { searchQuery = it },
                placeholder = { Text("Search...") },
                modifier = Modifier.fillMaxWidth().padding(12.dp),
                shape = RoundedCornerShape(12.dp),
                singleLine = true
            )

            ScrollableTabRow(selectedTabIndex = categories.indexOf(selectedCat).coerceAtLeast(0)) {
                categories.forEach { cat ->
                    Tab(selected = cat == selectedCat, onClick = { selectedCat = cat }, text = { Text(cat) })
                }
            }

            AnimatedVisibility(visible = showClassifier) {
                ClassifierPanel(
                    isLoading = isClassifying,
                    result = classifierResult,
                    reason = classifierReason,
                    onClassify = { mw, sol, bond, src, mon ->
                        isClassifying = true
                        classifierResult = null
                        classifierReason = null
                        
                        val features = mapOf(
                            "mw_kda" to mw,
                            "solubility" to sol,
                            "bond_type" to bond,
                            "source_origin" to src,
                            "monomer_unit" to mon
                        )
                        
                        val res = classifier.classify(features)
                        if (res != null) {
                            // APPLY SAFETY GATING
                            val gate = ClinicalSafetyManager.shouldShowPrediction(res.confidence)
                            if (gate.canShowPrediction) {
                                classifierResult = "Predicted: ${res.predictedClass} (${(res.confidence * 100).roundToInt()}% confidence)"
                                classifierReason = "Reference Classification (Research Use Only)"
                            } else {
                                classifierResult = "Prediction Gated"
                                classifierReason = gate.reason
                            }
                        } else {
                            classifierResult = "Error"
                            classifierReason = "Classification failed"
                        }
                        isClassifying = false
                    }
                )
            }

            LazyColumn(modifier = Modifier.fillMaxSize().padding(12.dp)) {
                items(filtered) { entry -> PolysaccharideCard(entry) }
            }
        }
    }
}

@Composable
fun ClassifierPanel(
    isLoading: Boolean,
    result: String?,
    reason: String?,
    onClassify: (Double, String, String, String, String) -> Unit
) {
    var mw by remember { mutableStateOf("500") }
    Surface(
        modifier = Modifier.fillMaxWidth().padding(8.dp),
        shape = RoundedCornerShape(12.dp),
        color = MaterialTheme.colorScheme.secondaryContainer
    ) {
        Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("🤖 ML Classifier", fontWeight = FontWeight.Bold)
            
            OutlinedTextField(value = mw, onValueChange = { mw = it }, label = { Text("MW (kDa)") })
            
            Button(onClick = { onClassify(mw.toDoubleOrNull() ?: 0.0, "Soluble", "Alpha-1,4", "Plants", "Glucose") },
                   enabled = !isLoading, modifier = Modifier.fillMaxWidth()) {
                if (isLoading) CircularProgressIndicator(modifier = Modifier.size(18.dp))
                else Text("Classify")
            }

            result?.let { Text(it, fontWeight = FontWeight.Bold) }
            reason?.let { Text(it, fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
        }
    }
}

@Composable
fun PolysaccharideCard(entry: PolysaccharideEntry) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(entry.name, fontWeight = FontWeight.Bold)
            Text(entry.category, fontSize = 12.sp, color = MaterialTheme.colorScheme.primary)
        }
    }
}
