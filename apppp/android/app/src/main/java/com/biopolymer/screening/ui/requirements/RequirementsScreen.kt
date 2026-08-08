package com.biopolymer.screening.ui.requirements

import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import kotlinx.coroutines.flow.collectLatest
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.biopolymer.screening.ui.components.AppTopBar
import com.biopolymer.screening.ui.components.ValidatedNumberField
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RequirementsScreen(
    onViewResults: () -> Unit,
    viewModel: RequirementsViewModel = hiltViewModel(),
) {
    val isLoading by viewModel.isLoading.collectAsState()
    val results by viewModel.results.collectAsState()
    val error by viewModel.error.collectAsState()
    val showInstructions by viewModel.showInstructions.collectAsState()

    LaunchedEffect(Unit) {
        viewModel.events.collectLatest { event ->
            when (event) {
                is RequirementsEvent.NavigateToResults -> {
                    onViewResults()
                }
            }
        }
    }

    BackHandler(enabled = viewModel.currentStep > 0) {
        viewModel.previousStep()
    }

    val progressText by viewModel.screeningProgressText.collectAsState()

    // Progressive Step Progress Dialog during Screening Execution
    if (isLoading) {
        AlertDialog(
            onDismissRequest = { /* Modal: Disable dismissal during execution */ },
            title = {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        Icons.Filled.AutoAwesome,
                        contentDescription = "AI Screening",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(28.dp)
                    )
                    Spacer(modifier = Modifier.width(12.dp))
                    Text("AI Material Screening", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(48.dp),
                        color = MaterialTheme.colorScheme.primary,
                        strokeWidth = 4.dp
                    )
                    Text(
                        text = progressText,
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onSurface,
                        fontWeight = FontWeight.Medium,
                        textAlign = TextAlign.Center
                    )
                }
            },
            confirmButton = {}
        )
    }

    // Instructions Dialog
    if (showInstructions) {
        AlertDialog(
            onDismissRequest = { viewModel.onInstructionsViewed() },
            icon = { Icon(Icons.Default.Lightbulb, contentDescription = null, tint = MaterialTheme.colorScheme.primary) },
            title = { Text("How it works") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("1. Define your material requirements across 7 categories.")
                    Text("2. Set priority weights for what matters most to your project.")
                    Text("3. Run the screening to get a ranked list of bio-polymers.")
                    Text("4. Save your results as Projects for future reference.")
                }
            },
            confirmButton = {
                TextButton(onClick = { viewModel.onInstructionsViewed() }) {
                    Text("Got it")
                }
            }
        )
    }

    // Error dialog
    if (error != null) {
        AlertDialog(
            onDismissRequest = { viewModel.clearError() },
            title = { Text("Screening Error") },
            text = { Text(error ?: "") },
            confirmButton = {
                TextButton(onClick = { viewModel.clearError() }) {
                    Text("OK")
                }
            }
        )
    }

    Scaffold(
        topBar = {
            AppTopBar(
                title = "New Screening",
                subtitle = "Step ${viewModel.currentStep + 1} of ${viewModel.totalSteps}",
                onNavigateBack = if (viewModel.currentStep > 0) { { viewModel.previousStep() } } else null
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            LinearProgressIndicator(
                progress = { (viewModel.currentStep + 1).toFloat() / viewModel.totalSteps },
                modifier = Modifier.fillMaxWidth(),
                color = MaterialTheme.colorScheme.primary,
                trackColor = MaterialTheme.colorScheme.surfaceVariant,
            )

            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                AnimatedContent(
                    targetState = viewModel.currentStep,
                    transitionSpec = {
                        if (targetState > initialState) {
                            (slideInHorizontally { it } + fadeIn()) togetherWith
                                    (slideOutHorizontally { -it } + fadeOut())
                        } else {
                            (slideInHorizontally { -it } + fadeIn()) togetherWith
                                    (slideOutHorizontally { it } + fadeOut())
                        }
                    },
                    label = "step"
                ) { step ->
                    Column(
                        modifier = Modifier
                            .fillMaxSize()
                            .verticalScroll(rememberScrollState())
                            .padding(24.dp)
                    ) {
                        when (step) {
                            0 -> MechanicalStep(viewModel)
                            1 -> BarrierStep(viewModel)
                            2 -> BiologicalStep(viewModel)
                            3 -> DegradationStep(viewModel)
                            4 -> ProcessingStep(viewModel)
                            5 -> SterilizationStep(viewModel)
                            6 -> SustainabilityAndCostStep(viewModel)
                            7 -> ReviewStep(viewModel)
                        }
                    }
                }
            }

            Surface(tonalElevation = 2.dp) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp)
                        .navigationBarsPadding(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    if (viewModel.currentStep > 0) {
                        OutlinedButton(
                            onClick = { viewModel.previousStep() },
                            modifier = Modifier
                                .weight(1f)
                                .height(56.dp),
                        ) {
                            Icon(
                                Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = "Back"
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                            Text("Back")
                        }
                    }

                    if (viewModel.currentStep < viewModel.totalSteps - 1) {
                        Button(
                            onClick = { viewModel.nextStep() },
                            modifier = Modifier
                                .weight(1f)
                                .height(56.dp),
                        ) {
                            Text("Next")
                            Spacer(modifier = Modifier.width(8.dp))
                            Icon(
                                Icons.AutoMirrored.Filled.ArrowForward,
                                contentDescription = "Next"
                            )
                        }
                    } else {
                        Button(
                            onClick = { 
                                viewModel.runScreening() 
                            },
                            enabled = !isLoading,
                            modifier = Modifier
                                .weight(1f)
                                .height(56.dp),
                        ) {
                            if (isLoading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(20.dp),
                                    strokeWidth = 2.dp,
                                    color = MaterialTheme.colorScheme.onPrimary,
                                )
                            } else {
                                Icon(Icons.Filled.Science, contentDescription = "Run Screening")
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("Run Screening")
                            }
                        }
                    }
                }
            }
        }
    }
}

// ── Step Composables ───────────────────────────────────────────────

@Composable
private fun MechanicalStep(viewModel: RequirementsViewModel) {
    // Info architecture / Medical Disclaimer on the very first step
    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.secondaryContainer),
        modifier = Modifier.padding(bottom = 16.dp).fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("AI-Assisted Polysaccharide Screening", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSecondaryContainer)
            Text("Find optimal sustainable biomedical packaging materials based on your constraints.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSecondaryContainer)
            Spacer(modifier = Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(4.dp))
                Text("Not a medical device. Reference tool only.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
            }
        }
    }

    Spacer(modifier = Modifier.height(16.dp))
    HorizontalDivider()
    Spacer(modifier = Modifier.height(16.dp))

    StepHeader(
        icon = Icons.Filled.FitnessCenter,
        title = "Mechanical Properties",
        subtitle = "Define tensile strength, modulus, and elongation targets."
    )
    Spacer(modifier = Modifier.height(32.dp))

    RangeInput(
        label = "Tensile Strength (MPa)",
        minValue = viewModel.mechanical.tensileStrengthMin?.toString() ?: "",
        maxValue = viewModel.mechanical.tensileStrengthMax?.toString() ?: "",
        onMinChange = {
            viewModel.mechanical = viewModel.mechanical.copy(tensileStrengthMin = it.toFloatOrNull())
        },
        onMaxChange = {
            viewModel.mechanical = viewModel.mechanical.copy(tensileStrengthMax = it.toFloatOrNull())
        },
    )
    Spacer(modifier = Modifier.height(24.dp))

    RangeInput(
        label = "Elastic Modulus (GPa)",
        minValue = viewModel.mechanical.elasticModulusMin?.toString() ?: "",
        maxValue = viewModel.mechanical.elasticModulusMax?.toString() ?: "",
        onMinChange = {
            viewModel.mechanical = viewModel.mechanical.copy(elasticModulusMin = it.toFloatOrNull())
        },
        onMaxChange = {
            viewModel.mechanical = viewModel.mechanical.copy(elasticModulusMax = it.toFloatOrNull())
        },
    )
    Spacer(modifier = Modifier.height(24.dp))

    RangeInput(
        label = "Elongation at Break (%)",
        minValue = viewModel.mechanical.elongationMin?.toString() ?: "",
        maxValue = viewModel.mechanical.elongationMax?.toString() ?: "",
        onMinChange = {
            viewModel.mechanical = viewModel.mechanical.copy(elongationMin = it.toFloatOrNull())
        },
        onMaxChange = {
            viewModel.mechanical = viewModel.mechanical.copy(elongationMax = it.toFloatOrNull())
        },
    )

    Spacer(modifier = Modifier.height(16.dp))

    WeightSlider(
        label = "Mechanical Priority Weight",
        value = viewModel.mechanical.weight,
        onValueChange = { viewModel.mechanical = viewModel.mechanical.copy(weight = it) }
    )
}

@Composable
private fun BarrierStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Shield,
        title = "Barrier Properties",
        subtitle = "Define water vapor and oxygen transmission targets."
    )
    Spacer(modifier = Modifier.height(32.dp))

    @Suppress("SpellCheckingInspection")
    NumberInput(
        label = "Max WVTR (g/m\u00B2/day)",
        value = viewModel.barrier.wvtrMax?.toString() ?: "",
        onValueChange = { viewModel.barrier = viewModel.barrier.copy(wvtrMax = it.toFloatOrNull()) }
    )
    Spacer(modifier = Modifier.height(24.dp))

    NumberInput(
        label = "Max OTR (cc/m\u00B2/day)",
        value = viewModel.barrier.otrMax?.toString() ?: "",
        onValueChange = { viewModel.barrier = viewModel.barrier.copy(otrMax = it.toFloatOrNull()) }
    )

    Spacer(modifier = Modifier.height(16.dp))

    WeightSlider(
        label = "Barrier Priority Weight",
        value = viewModel.barrier.weight,
        onValueChange = { viewModel.barrier = viewModel.barrier.copy(weight = it) }
    )
}

@Composable
private fun BiologicalStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Biotech,
        title = "Biological Requirements",
        subtitle = "Specify biocompatibility and safety requirements."
    )
    Spacer(modifier = Modifier.height(32.dp))

    SwitchRow(
        label = "Cytotoxicity Safety Required",
        checked = viewModel.biological.cytotoxicitySafeRequired,
        onCheckedChange = {
            viewModel.biological = viewModel.biological.copy(cytotoxicitySafeRequired = it)
        }
    )
    SwitchRow(
        label = "Hemocompatibility Required",
        checked = viewModel.biological.hemocompatibleRequired,
        onCheckedChange = {
            viewModel.biological = viewModel.biological.copy(hemocompatibleRequired = it)
        }
    )
    SwitchRow(
        label = "Antimicrobial Required",
        checked = viewModel.biological.antimicrobialRequired,
        onCheckedChange = {
            viewModel.biological = viewModel.biological.copy(antimicrobialRequired = it)
        }
    )

    Spacer(modifier = Modifier.height(16.dp))
    WeightSlider(
        label = "Biological Priority Weight",
        value = viewModel.biological.weight,
        onValueChange = { viewModel.biological = viewModel.biological.copy(weight = it) }
    )
}

@Composable
private fun DegradationStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Recycling,
        title = "Degradation Profile",
        subtitle = "Define biodegradation timeframe and stability."
    )
    Spacer(modifier = Modifier.height(32.dp))

    RangeInput(
        label = "Degradation Window (days)",
        minValue = viewModel.degradation.degradationDaysMin?.toString() ?: "",
        maxValue = viewModel.degradation.degradationDaysMax?.toString() ?: "",
        onMinChange = {
            viewModel.degradation = viewModel.degradation.copy(degradationDaysMin = it.toIntOrNull())
        },
        onMaxChange = {
            viewModel.degradation = viewModel.degradation.copy(degradationDaysMax = it.toIntOrNull())
        },
    )
    Spacer(modifier = Modifier.height(24.dp))

    SwitchRow(
        label = "Enzymatic Degradability Required",
        checked = viewModel.degradation.enzymaticRequired,
        onCheckedChange = {
            viewModel.degradation = viewModel.degradation.copy(enzymaticRequired = it)
        }
    )

    Spacer(modifier = Modifier.height(16.dp))
    WeightSlider(
        label = "Degradation Priority Weight",
        value = viewModel.degradation.weight,
        onValueChange = { viewModel.degradation = viewModel.degradation.copy(weight = it) }
    )
}

@Composable
private fun ProcessingStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Build,
        title = "Processing Methods",
        subtitle = "Select required processing capabilities."
    )
    Spacer(modifier = Modifier.height(32.dp))

    SwitchRow("Film Formation", viewModel.processing.filmRequired) {
        viewModel.processing = viewModel.processing.copy(filmRequired = it)
    }
    SwitchRow("Casting", viewModel.processing.castingRequired) {
        viewModel.processing = viewModel.processing.copy(castingRequired = it)
    }
    SwitchRow("Extrusion", viewModel.processing.extrusionRequired) {
        viewModel.processing = viewModel.processing.copy(extrusionRequired = it)
    }
    SwitchRow("Coating", viewModel.processing.coatingRequired) {
        viewModel.processing = viewModel.processing.copy(coatingRequired = it)
    }
    SwitchRow("Melt Processing", viewModel.processing.meltRequired) {
        viewModel.processing = viewModel.processing.copy(meltRequired = it)
    }
}

@Composable
private fun SterilizationStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.CleaningServices,
        title = "Sterilization Compatibility",
        subtitle = "Select required sterilization methods (hard constraint)."
    )
    Spacer(modifier = Modifier.height(8.dp))

    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f)
        )
    ) {
        Row(modifier = Modifier.padding(12.dp)) {
            Icon(
                Icons.Filled.Warning,
                contentDescription = "Warning",
                tint = MaterialTheme.colorScheme.error,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                "Materials not supporting selected methods will be excluded entirely.",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
    Spacer(modifier = Modifier.height(12.dp))

    SwitchRow("Gamma Irradiation", viewModel.sterilization.gammaRequired) {
        viewModel.sterilization = viewModel.sterilization.copy(gammaRequired = it)
    }
    SwitchRow("Ethylene Oxide (EtO)", viewModel.sterilization.etoRequired) {
        viewModel.sterilization = viewModel.sterilization.copy(etoRequired = it)
    }
    SwitchRow("Steam", viewModel.sterilization.steamRequired) {
        viewModel.sterilization = viewModel.sterilization.copy(steamRequired = it)
    }
    SwitchRow("UV Irradiation", viewModel.sterilization.uvRequired) {
        viewModel.sterilization = viewModel.sterilization.copy(uvRequired = it)
    }
    SwitchRow("Autoclave", viewModel.sterilization.autoclaveRequired) {
        viewModel.sterilization = viewModel.sterilization.copy(autoclaveRequired = it)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SustainabilityAndCostStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Eco,
        title = "Sustainability & Cost",
        subtitle = "Set cost and availability preferences."
    )
    Spacer(modifier = Modifier.height(16.dp))

    Text("Maximum Cost Band", style = MaterialTheme.typography.titleSmall)
    Spacer(modifier = Modifier.height(8.dp))
    BandSelector(
        selectedBand = viewModel.cost.maxCostBand,
        onBandSelected = { viewModel.cost = viewModel.cost.copy(maxCostBand = it) }
    )

    Spacer(modifier = Modifier.height(16.dp))
    Text("Minimum Availability", style = MaterialTheme.typography.titleSmall)
    Spacer(modifier = Modifier.height(8.dp))
    BandSelector(
        selectedBand = viewModel.cost.minAvailabilityBand,
        onBandSelected = { viewModel.cost = viewModel.cost.copy(minAvailabilityBand = it) }
    )

    Spacer(modifier = Modifier.height(24.dp))
}

// ── Reusable Input Components ───────────────────────────────────────────────

@Composable
private fun StepHeader(icon: ImageVector, title: String, subtitle: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Surface(
            shape = MaterialTheme.shapes.medium,
            color = MaterialTheme.colorScheme.primaryContainer,
            modifier = Modifier.size(48.dp),
        ) {
            Box(contentAlignment = Alignment.Center) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
        }
        Spacer(modifier = Modifier.width(12.dp))
        Column {
            Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun ReviewStep(viewModel: RequirementsViewModel) {
    StepHeader(
        icon = Icons.Filled.Checklist,
        title = "Confirm Requirements",
        subtitle = "Review your configuration before screening."
    )
    Spacer(modifier = Modifier.height(16.dp))

    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
        ),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Ready to Screen", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Priority Weights:", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
            Text("• Mechanical: ${viewModel.mechanical.weight}", style = MaterialTheme.typography.bodySmall)
            Text("• Barrier: ${viewModel.barrier.weight}", style = MaterialTheme.typography.bodySmall)
            Text("• Degradation: ${viewModel.degradation.weight}", style = MaterialTheme.typography.bodySmall)
            Spacer(modifier = Modifier.height(16.dp))
            Text("Tap 'Run Screening' to evaluate materials.", style = MaterialTheme.typography.bodyMedium)
        }
    }
}

@Composable
private fun NumberInput(label: String, value: String, onValueChange: (String) -> Unit) {
    ValidatedNumberField(
        label = label,
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth()
    )
}

@Composable
private fun RangeInput(
    label: String,
    minValue: String,
    maxValue: String,
    onMinChange: (String) -> Unit,
    onMaxChange: (String) -> Unit,
) {
    Text(label, style = MaterialTheme.typography.titleSmall)
    Spacer(modifier = Modifier.height(4.dp))
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        ValidatedNumberField(
            label = "Min",
            value = minValue,
            onValueChange = onMinChange,
            modifier = Modifier.weight(1f)
        )
        ValidatedNumberField(
            label = "Max",
            value = maxValue,
            onValueChange = onMaxChange,
            modifier = Modifier.weight(1f)
        )
    }
}

@Composable
private fun SwitchRow(label: String, checked: Boolean, onCheckedChange: (Boolean) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, style = MaterialTheme.typography.bodyLarge)
        Switch(checked = checked, onCheckedChange = onCheckedChange)
    }
}

@Composable
private fun WeightSlider(label: String, value: Float, onValueChange: (Float) -> Unit) {
    Text(
        "$label: ${String.format(Locale.US, "%.1f", value)}",
        style = MaterialTheme.typography.titleSmall,
        color = MaterialTheme.colorScheme.primary,
    )
    Slider(
        value = value,
        onValueChange = onValueChange,
        valueRange = 0f..3f,
        steps = 5,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun BandSelector(selectedBand: String?, onBandSelected: (String?) -> Unit) {
    val bands = listOf("low" to "Low", "med" to "Medium", "high" to "High")
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        bands.forEach { (value, label) ->
            FilterChip(
                selected = selectedBand == value,
                onClick = { onBandSelected(if (selectedBand == value) null else value) },
                label = { Text(label) },
            )
        }
    }
}
