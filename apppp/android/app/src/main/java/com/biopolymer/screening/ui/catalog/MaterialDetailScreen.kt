package com.biopolymer.screening.ui.catalog

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.biopolymer.screening.domain.model.Material
import com.biopolymer.screening.data.repository.MaterialRepository
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class MaterialDetailViewModel @Inject constructor(
    private val materialRepository: MaterialRepository,
) : ViewModel() {
    private val _material = MutableStateFlow<Material?>(null)
    val material: StateFlow<Material?> = _material

    fun loadMaterial(id: String) {
        viewModelScope.launch {
            _material.value = materialRepository.getMaterialById(id)
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MaterialDetailScreen(
    materialId: String,
    onNavigateBack: () -> Unit,
    viewModel: MaterialDetailViewModel = hiltViewModel(),
) {
    LaunchedEffect(materialId) {
        viewModel.loadMaterial(materialId)
    }

    val material by viewModel.material.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(material?.name ?: "Material Detail") },
                navigationIcon = {
                    IconButton(onClick = onNavigateBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        }
    ) { padding ->
        val mat = material
        if (mat == null) {
            Box(modifier = Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                // Header
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.4f))) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text(mat.name, style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        Text(mat.category.replaceFirstChar { it.uppercase() }, style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
                        mat.source?.let { Text("Source: $it", style = MaterialTheme.typography.bodyMedium) }
                        Text("Evidence: ${mat.evidenceLevel.uppercase()}", style = MaterialTheme.typography.labelLarge)
                    }
                }

                // Mechanical Properties
                PropertySection("⚙ Mechanical Properties") {
                    PropertyRow("Tensile Strength", mat.properties.tensileStrengthMin, mat.properties.tensileStrengthMax, "MPa")
                    PropertyRow("Elastic Modulus", mat.properties.elasticModulusMin, mat.properties.elasticModulusMax, "GPa")
                    PropertyRow("Elongation at Break", mat.properties.elongationMin, mat.properties.elongationMax, "%")
                    SinglePropertyRow("Puncture Resistance", mat.properties.punctureResistance?.let { "$it N" })
                }

                // Barrier Properties
                PropertySection("🛡 Barrier Properties") {
                    SinglePropertyRow("WVTR", mat.properties.wvtr?.let { "$it g/m²/day" })
                    SinglePropertyRow("OTR", mat.properties.otr?.let { "$it cc/m²/day" })
                }

                // Biological Properties
                PropertySection("🧬 Biological Properties") {
                    BoolPropertyRow("Cytotoxicity Safe", mat.properties.cytotoxicitySafe)
                    BoolPropertyRow("Hemocompatible", mat.properties.hemocompatible)
                    BoolPropertyRow("Antimicrobial", mat.properties.antimicrobial)
                    SinglePropertyRow("Endotoxin Concern", mat.properties.endotoxinConcern)
                }

                // Degradation
                PropertySection("♻ Degradation") {
                    PropertyRow("Degradation Time", mat.properties.degradationDaysMin?.toFloat(), mat.properties.degradationDaysMax?.toFloat(), "days")
                    BoolPropertyRow("Enzymatic Degradability", mat.properties.enzymaticDegradability)
                    SinglePropertyRow("Hydrolytic Stability", mat.properties.hydrolyticStability?.uppercase())
                }

                // Sterilization
                PropertySection("🔬 Sterilization Compatibility") {
                    BoolPropertyRow("Gamma", mat.properties.sterGamma)
                    BoolPropertyRow("EtO", mat.properties.sterEto)
                    BoolPropertyRow("Steam", mat.properties.sterSteam)
                    BoolPropertyRow("UV", mat.properties.sterUv)
                    BoolPropertyRow("Autoclave", mat.properties.sterAutoclave)
                }

                // Processing
                PropertySection("🏭 Processing Methods") {
                    BoolPropertyRow("Film", mat.properties.procFilm)
                    BoolPropertyRow("Casting", mat.properties.procCasting)
                    BoolPropertyRow("Extrusion", mat.properties.procExtrusion)
                    BoolPropertyRow("Coating", mat.properties.procCoating)
                    BoolPropertyRow("Melt Processing", mat.properties.procMelt)
                    SinglePropertyRow("Solvents", mat.properties.solventCompatible)
                }

                // Cost & Availability
                PropertySection("💰 Cost & Availability") {
                    SinglePropertyRow("Cost Band", mat.properties.costBand?.uppercase())
                    SinglePropertyRow("Availability", mat.properties.availabilityBand?.uppercase())
                }

                // Notes
                Card {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Notes", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(mat.notes ?: "Not Available", style = MaterialTheme.typography.bodyMedium)
                    }
                }

                // Data completeness
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f))) {
                    Column(modifier = Modifier.padding(16.dp)) {
                        Text("Data Completeness", style = MaterialTheme.typography.titleSmall)
                        Spacer(modifier = Modifier.height(8.dp))
                        LinearProgressIndicator(
                            progress = { (mat.properties.dataCompleteness).coerceIn(0f, 1f) },
                            modifier = Modifier.fillMaxWidth()
                        )
                        Text("${"%.0f".format((mat.properties.dataCompleteness * 100).coerceIn(0f, 100f))}%", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }
    }
}

@Composable
fun PropertySection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            content()
        }
    }
}

@Composable
fun PropertyRow(label: String, min: Float?, max: Float?, unit: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        val valueText = when {
            min != null && max != null -> "$min – $max $unit"
            min != null -> "$min $unit"
            max != null -> "$max $unit"
            else -> "Not Available"
        }
        Text(
            valueText,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            color = if (valueText == "Not Available") MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.onSurface
        )
    }
}

@Composable
fun SinglePropertyRow(label: String, value: String?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        val displayVal = if (value.isNullOrBlank()) "Not Available" else value
        Text(
            displayVal,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            color = if (displayVal == "Not Available") MaterialTheme.colorScheme.outline else MaterialTheme.colorScheme.onSurface
        )
    }
}


@Composable
fun BoolPropertyRow(label: String, value: Boolean?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 2.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium)
        when (value) {
            true -> Icon(Icons.Filled.CheckCircle, contentDescription = "Yes", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(20.dp))
            false -> Icon(Icons.Filled.Cancel, contentDescription = "No", tint = MaterialTheme.colorScheme.error, modifier = Modifier.size(20.dp))
            null -> Text("Not Available", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.outline)
        }
    }
}

