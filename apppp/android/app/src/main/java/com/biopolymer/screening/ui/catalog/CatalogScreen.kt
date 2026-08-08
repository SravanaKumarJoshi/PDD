package com.biopolymer.screening.ui.catalog

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.biopolymer.screening.domain.model.MaterialCardModel
import com.biopolymer.screening.ui.theme.ConfidenceHigh
import com.biopolymer.screening.ui.theme.ConfidenceLow
import com.biopolymer.screening.ui.theme.ConfidenceMed

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CatalogScreen(
    onMaterialClick: (String) -> Unit,
    viewModel: CatalogViewModel = hiltViewModel(),
) {
    val materials by viewModel.materials.collectAsStateWithLifecycle()
    val categories by viewModel.categories.collectAsStateWithLifecycle()
    val searchQuery by viewModel.searchQuery.collectAsStateWithLifecycle()
    val selectedCategory by viewModel.selectedCategory.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Materials Catalog") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            // Search bar
            OutlinedTextField(
                value = searchQuery,
                onValueChange = viewModel::onSearchQueryChanged,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text("Search materials...") },
                leadingIcon = { Icon(Icons.Filled.Search, contentDescription = "Search") },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { viewModel.onSearchQueryChanged("") }) {
                            Icon(Icons.Filled.Clear, contentDescription = "Clear search")
                        }
                    }
                },
                singleLine = true,
            )

            // Category chips
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(8.dp),
                contentPadding = PaddingValues(horizontal = 16.dp),
            ) {
                item {
                    FilterChip(
                        selected = selectedCategory == null,
                        onClick = { viewModel.onCategorySelected(null) },
                        label = { Text("All") },
                    )
                }
                items(categories, key = { it }) { category ->
                    val isSelected = selectedCategory == category
                    FilterChip(
                        selected = isSelected,
                        onClick = { viewModel.onCategorySelected(if (isSelected) null else category) },
                        label = { Text(category.replaceFirstChar { it.uppercase() }) },
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Materials list
            if (materials.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Filled.Inventory2, contentDescription = null, modifier = Modifier.size(64.dp), tint = MaterialTheme.colorScheme.outline)
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("No materials found", style = MaterialTheme.typography.titleMedium)
                    }
                }
            } else {
                LazyColumn(
                    contentPadding = PaddingValues(horizontal = 20.dp, vertical = 24.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(materials, key = { it.id }) { material ->
                        MaterialListItem(
                            material = material,
                            onClick = { onMaterialClick(material.id) }
                        )
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MaterialListItem(material: MaterialCardModel, onClick: () -> Unit) {
    ElevatedCard(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Category icon
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier.size(44.dp),
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(Icons.Filled.Science, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(material.name, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(
                        "Type: ${material.category.replaceFirstChar { it.uppercase() }}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.primary,
                        fontWeight = FontWeight.Medium
                    )
                }

                // Evidence badge
                AssistChip(
                    onClick = {},
                    label = { Text(material.evidenceLevel.uppercase(), style = MaterialTheme.typography.labelSmall) },
                    colors = AssistChipDefaults.assistChipColors(
                        containerColor = when (material.evidenceLevel) {
                            "high" -> ConfidenceHigh.copy(alpha = 0.15f)
                            "med" -> ConfidenceMed.copy(alpha = 0.15f)
                            else -> ConfidenceLow.copy(alpha = 0.15f)
                        }
                    ),
                    modifier = Modifier.height(28.dp),
                )
            }

            // Short Description
            Text(
                text = material.descriptionText,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
            )

            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f))

            // 2-3 Key properties preview
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                val tensileStr = remember(material.tensileStrengthMin, material.tensileStrengthMax) {
                    when {
                        material.tensileStrengthMin != null && material.tensileStrengthMax != null ->
                            "${material.tensileStrengthMin} - ${material.tensileStrengthMax} MPa"
                        material.tensileStrengthMin != null -> "${material.tensileStrengthMin} MPa"
                        else -> "Not Available"
                    }
                }

                val degDays = remember(material.degradationDaysMin, material.degradationDaysMax) {
                    when {
                        material.degradationDaysMin != null && material.degradationDaysMax != null ->
                            "${material.degradationDaysMin} - ${material.degradationDaysMax} d"
                        material.degradationDaysMin != null -> "${material.degradationDaysMin} d"
                        else -> "Not Available"
                    }
                }

                val safetyStr = remember(material.cytotoxicitySafe) {
                    when (material.cytotoxicitySafe) {
                        true -> "Safe"
                        false -> "Unsafe"
                        null -> "Not Available"
                    }
                }

                Column {
                    Text("Tensile", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                    Text(tensileStr, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                }

                Column {
                    Text("Degradation", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                    Text(degDays, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                }

                Column {
                    Text("Safety", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
                    Text(safetyStr, style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                }
            }
        }
    }
}

