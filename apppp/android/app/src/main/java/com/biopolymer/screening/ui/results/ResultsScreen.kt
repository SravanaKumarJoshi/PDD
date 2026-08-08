package com.biopolymer.screening.ui.results

import android.util.Log
import android.widget.Toast
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.OpenInNew
import androidx.compose.material.icons.filled.OpenInNew
import androidx.compose.material.icons.filled.Save
import androidx.compose.material.icons.filled.SearchOff
import androidx.compose.material.icons.filled.Home
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.ElevatedCard
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.biopolymer.screening.domain.model.FactorContribution
import com.biopolymer.screening.domain.model.Recommendation
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.biopolymer.screening.ui.requirements.RequirementsViewModel
import com.biopolymer.screening.ui.theme.ConfidenceHigh
import com.biopolymer.screening.ui.theme.ConfidenceLow
import com.biopolymer.screening.ui.theme.ConfidenceMed
import com.biopolymer.screening.ui.theme.OnPrimary
import com.biopolymer.screening.ui.theme.ScoreExcellent
import com.biopolymer.screening.ui.theme.ScoreFair
import com.biopolymer.screening.ui.theme.ScoreGood
import com.biopolymer.screening.ui.theme.ScorePoor
import com.biopolymer.screening.ui.components.AppTopBar
import com.biopolymer.screening.ui.components.MetricChip
import com.biopolymer.screening.ui.components.EvidenceBadge
import com.squareup.moshi.Moshi
import java.util.Locale
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.Button

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(
    onNavigateBack: () -> Unit,
    onMaterialDetail: (String) -> Unit,
    onNavigateHome: () -> Unit,
    viewModel: RequirementsViewModel = hiltViewModel(),
) {
    val results by viewModel.results.collectAsState()
    val scoringResult = results
    var showJsonView by remember { mutableStateOf(false) }
    
    // Debug logging - comprehensive
    Log.d("ResultsScreen", "=== ResultsScreen COMPOSING ===")
    Log.d("ResultsScreen", "scoringResult == null: ${scoringResult == null}")
    if (scoringResult != null) {
        Log.d("ResultsScreen", "recommendations.size: ${scoringResult.recommendations.size}")
        Log.d("ResultsScreen", "totalEvaluated: ${scoringResult.totalEvaluated}")
        Log.d("ResultsScreen", "filteredOut: ${scoringResult.filteredOut}")
        Log.d("ResultsScreen", "limitingConstraints.size: ${scoringResult.limitingConstraints.size}")
        
        // Log JSON representation
        try {
            val moshi = Moshi.Builder().build()
            val adapter = moshi.adapter(ScoringEngine.ScoringResult::class.java)
            val jsonStr = adapter.toJson(scoringResult)
            Log.d("ResultsScreen", "JSON Output: $jsonStr")
        } catch (e: Exception) {
            Log.e("ResultsScreen", "Failed to convert to JSON: ${e.message}", e)
        }
    } else {
        Log.w("ResultsScreen", "WARNING: scoringResult is NULL!")
    }

    val context = LocalContext.current
    var showSaveDialog by remember { mutableStateOf(false) }
    var projectName by remember { mutableStateOf("Polysaccharide Screening") }

    var sortMode by remember { mutableStateOf("Best match") }
    val sortedRecommendations = remember(scoringResult, sortMode) {
        when (sortMode) {
            "Highest confidence" -> scoringResult?.recommendations?.sortedByDescending { it.confidence } ?: emptyList()
            else -> scoringResult?.recommendations ?: emptyList()
        }
    }

    var duplicateDetected by remember { mutableStateOf(false) }

    if (showSaveDialog) {
        AlertDialog(
            onDismissRequest = {
                showSaveDialog = false
                duplicateDetected = false
            },
            title = { Text(if (duplicateDetected) "Duplicate Screening" else "Save Screening Results") },
            text = {
                Column {
                    if (duplicateDetected) {
                        Text(
                            "An identical screening result already exists in local storage. Would you like to overwrite it?",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Spacer(modifier = Modifier.height(12.dp))
                    }
                    OutlinedTextField(
                        value = projectName,
                        onValueChange = {
                            projectName = it
                            duplicateDetected = false
                        },
                        label = { Text("Project / Screening Title") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                TextButton(
                    onClick = {
                        if (projectName.isNotBlank()) {
                            viewModel.saveAsProject(
                                title = projectName,
                                overwrite = duplicateDetected,
                                onSuccess = {
                                    Toast.makeText(context, if (duplicateDetected) "Screening updated successfully" else "Screening saved successfully", Toast.LENGTH_SHORT).show()
                                    showSaveDialog = false
                                    duplicateDetected = false
                                },
                                onDuplicate = {
                                    duplicateDetected = true
                                },
                                onError = { errorMsg ->
                                    Toast.makeText(context, "Failed to save: $errorMsg", Toast.LENGTH_LONG).show()
                                }
                            )
                        }
                    }
                ) {
                    Text(if (duplicateDetected) "Overwrite" else "Save")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = {
                        showSaveDialog = false
                        duplicateDetected = false
                    }
                ) {
                    Text("Cancel")
                }
            }
        )
    }


    Scaffold(
        topBar = {
            AppTopBar(
                title = "Screening Results",
                onNavigateBack = onNavigateBack,
                actions = {
                    if (scoringResult != null) {
                        IconButton(onClick = { showJsonView = !showJsonView }) {
                            Text("JSON", style = MaterialTheme.typography.labelSmall)
                        }
                        IconButton(onClick = { showSaveDialog = true }) {
                            Icon(Icons.Filled.Save, contentDescription = "Save Project")
                        }
                    }
                    IconButton(onClick = onNavigateHome) {
                        Icon(Icons.Filled.Home, contentDescription = "Home")
                    }
                }
            )
        }
    ) { padding ->
        if (showJsonView && scoringResult != null) {
            // JSON View
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding)
            ) {
                val moshi = Moshi.Builder().build()
                val adapter = moshi.adapter(ScoringEngine.ScoringResult::class.java)
                val jsonStr = try {
                    adapter.toJson(scoringResult)
                } catch (e: Exception) {
                    "Error converting to JSON: ${e.message}"
                }
                
                Surface(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(16.dp),
                    color = MaterialTheme.colorScheme.surface
                ) {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(12.dp),
                        contentPadding = PaddingValues(bottom = 16.dp)
                    ) {
                        item {
                            Text(
                                "Results as JSON:",
                                style = MaterialTheme.typography.titleSmall,
                                fontWeight = FontWeight.Bold,
                                modifier = Modifier.padding(bottom = 12.dp)
                            )
                        }
                        item {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .horizontalScroll(rememberScrollState()),
                                color = MaterialTheme.colorScheme.surfaceVariant,
                                shape = MaterialTheme.shapes.small
                            ) {
                                Text(
                                    jsonStr,
                                    style = MaterialTheme.typography.bodySmall,
                                    modifier = Modifier.padding(12.dp),
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    fontFamily = androidx.compose.ui.text.font.FontFamily.Monospace
                                )
                            }
                        }
                    }
                }
            }
        } else if (scoringResult == null || scoringResult.recommendations.isEmpty()) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(24.dp)) {
                    Icon(
                        Icons.Filled.SearchOff,
                        contentDescription = null,
                        modifier = Modifier.size(64.dp),
                        tint = MaterialTheme.colorScheme.outline
                    )
                    Spacer(modifier = Modifier.height(16.dp))
                    
                    if (scoringResult == null) {
                        Text(
                            "No results yet",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            "Run a screening to see recommendations.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        Text(
                            "No matching materials found",
                            style = MaterialTheme.typography.titleMedium
                        )
                    }
                    
                    Spacer(modifier = Modifier.height(8.dp))

                    if (scoringResult?.limitingConstraints?.isNotEmpty() == true) {
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.3f)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text("Top Limiting Constraints:", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.error)
                                Spacer(modifier = Modifier.height(8.dp))
                                scoringResult.limitingConstraints.take(3).forEach { failed ->
                                    Text("• ${failed.reason} (${failed.failureCount} failed)", style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                        Spacer(modifier = Modifier.height(24.dp))
                        androidx.compose.material3.Button(onClick = {
                            viewModel.relaxConstraints()
                            onNavigateBack()
                        }) {
                            Text("Relax Constraints")
                        }
                    }
                    
                    // Debug info for troubleshooting
                    if (scoringResult != null) {
                        Spacer(modifier = Modifier.height(24.dp))
                        Card(
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant
                            ),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Text(
                                    "Debug Info",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.outline
                                )
                                Text(
                                    "Total: ${scoringResult.totalEvaluated} | Matched: ${scoringResult.recommendations.size} | Filtered: ${scoringResult.filteredOut}",
                                    style = MaterialTheme.typography.bodySmall,
                                    modifier = Modifier.padding(top = 8.dp)
                                )
                            }
                        }
                    }
                }
            }
        } else {
            LazyColumn(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
                verticalArrangement = Arrangement.spacedBy(20.dp),
            ) {
                item {
                    SummaryCard(scoringResult)
                    Spacer(modifier = Modifier.height(8.dp))
                    
                    androidx.compose.material3.OutlinedButton(
                        onClick = {
                            val intent = android.content.Intent(
                                android.content.Intent.ACTION_VIEW,
                                android.net.Uri.parse("http://localhost:8000/catalog")
                            )
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        androidx.compose.material3.Icon(Icons.AutoMirrored.Filled.OpenInNew, contentDescription = null, modifier = Modifier.size(18.dp))
                        androidx.compose.foundation.layout.Spacer(modifier = Modifier.width(8.dp))
                        androidx.compose.material3.Text("View Complete Material Catalogue on Web")
                    }
                    Spacer(modifier = Modifier.height(8.dp))
                }

                item {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("Sort by:", style = MaterialTheme.typography.labelMedium)
                        androidx.compose.material3.FilterChip(
                            selected = sortMode == "Best match",
                            onClick = { sortMode = "Best match" },
                            label = { Text("Best match") }
                        )
                        androidx.compose.material3.FilterChip(
                            selected = sortMode == "Highest confidence",
                            onClick = { sortMode = "Highest confidence" },
                            label = { Text("Confidence") }
                        )
                    }
                }

                items(
                    items = sortedRecommendations,
                    key = { it.materialId }
                ) { rec ->
                    RecommendationCard(
                        recommendation = rec,
                        rank = scoringResult.recommendations.indexOf(rec) + 1,
                        onClick = { onMaterialDetail(rec.materialId) }
                    )
                }
            }
        }
    }
}

@Composable
private fun SummaryCard(result: ScoringEngine.ScoringResult) {
    Card(
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f)
        )
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                "Screening Summary",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Spacer(modifier = Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                SummaryChip("${result.totalEvaluated}", "Materials Analyzed")
                SummaryChip("${result.filteredOut}", "Filtered Out")
                SummaryChip("${result.recommendations.size}", "Matched")
            }
        }
    }
}

@Composable
private fun SummaryChip(value: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            value,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun RecommendationCard(
    recommendation: Recommendation,
    rank: Int,
    onClick: () -> Unit,
) {
    var expanded by remember { mutableStateOf(false) }

    ElevatedCard(
        onClick = { expanded = !expanded },
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = when (rank) {
                        1 -> ScoreExcellent
                        2 -> ScoreGood
                        3 -> ScoreFair
                        else -> MaterialTheme.colorScheme.outline
                    },
                    modifier = Modifier.size(36.dp),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Text(
                            "#$rank",
                            color = OnPrimary,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleSmall
                        )
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        recommendation.materialName,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        recommendation.category.replaceFirstChar { it.uppercase() },
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }

                Column(horizontalAlignment = Alignment.End) {
                    MetricChip(value = recommendation.score, label = "Match")
                    Spacer(modifier = Modifier.height(4.dp))
                    // Provide a default evidence string if not in model, or assume Med/High for now
                    EvidenceBadge(evidenceLevel = if (recommendation.confidence > 0.6f) "High" else "Med")
                }
            }

            AnimatedVisibility(visible = expanded) {
                Column(modifier = Modifier.padding(top = 12.dp)) {
                    HorizontalDivider()
                    Spacer(modifier = Modifier.height(12.dp))

                    if (recommendation.topFactors.isNotEmpty()) {
                        Text(
                            "\u2705 Strengths",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = ScoreExcellent
                        )
                        recommendation.topFactors.forEach { factor ->
                            FactorRow(factor, isPositive = true)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    if (recommendation.concerns.isNotEmpty()) {
                        Text(
                            "\u26A0 Concerns",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = ScorePoor
                        )
                        recommendation.concerns.forEach { factor ->
                            FactorRow(factor, isPositive = false)
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    if (recommendation.tradeoffs.isNotEmpty()) {
                        Text(
                            "\uD83D\uDCA1 Trade-offs",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold
                        )
                        recommendation.tradeoffs.forEach { tradeoff ->
                            Text(
                                "\u2022 $tradeoff",
                                style = MaterialTheme.typography.bodySmall,
                                modifier = Modifier.padding(start = 8.dp, top = 2.dp)
                            )
                        }
                        Spacer(modifier = Modifier.height(8.dp))
                    }

                    TextButton(onClick = onClick) {
                        Icon(
                            Icons.AutoMirrored.Filled.OpenInNew,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("View Material Profile")
                    }
                }
            }
        }
    }
}

@Composable
private fun FactorRow(factor: FactorContribution, isPositive: Boolean) {
    Row(
        modifier = Modifier.padding(start = 8.dp, top = 2.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        LinearProgressIndicator(
            progress = { factor.score },
            modifier = Modifier
                .width(40.dp)
                .height(4.dp),
            color = if (isPositive) ScoreGood else ScorePoor,
            trackColor = MaterialTheme.colorScheme.surfaceVariant,
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(factor.description, style = MaterialTheme.typography.bodySmall)
    }
}

private fun scoreColor(score: Float) = when {
    score >= 0.8f -> ScoreExcellent
    score >= 0.6f -> ScoreGood
    score >= 0.4f -> ScoreFair
    else -> ScorePoor
}

private fun confidenceColor(confidence: Float) = when {
    confidence >= 0.7f -> ConfidenceHigh
    confidence >= 0.4f -> ConfidenceMed
    else -> ConfidenceLow
}
