package com.biopolymer.screening.ui.projects

import android.util.Log
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.icons.outlined.StarBorder
import androidx.compose.material.icons.automirrored.filled.Sort
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.biopolymer.screening.data.repository.SavedScreeningRepository
import com.biopolymer.screening.data.repository.SavedScreeningSortOrder
import com.biopolymer.screening.domain.model.SavedScreening
import com.biopolymer.screening.ui.components.MetricChip
import com.biopolymer.screening.ui.components.EvidenceBadge
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.*
import javax.inject.Inject

private const val TAG = "ProjectsViewModel"

@HiltViewModel
class ProjectsViewModel @Inject constructor(
    private val savedScreeningRepository: SavedScreeningRepository,
) : ViewModel() {

    private val _searchQuery = MutableStateFlow("")
    val searchQuery = _searchQuery.asStateFlow()

    private val _sortOrder = MutableStateFlow(SavedScreeningSortOrder.NEWEST_FIRST)
    val sortOrder = _sortOrder.asStateFlow()

    private val _favoritesOnly = MutableStateFlow(false)
    val favoritesOnly = _favoritesOnly.asStateFlow()

    init {
        viewModelScope.launch {
            try {
                savedScreeningRepository.syncWithBackend()
            } catch (e: Exception) {
                Log.w(TAG, "ProjectsViewModel init sync failed: ${e.message}")
            }
        }
    }

    @OptIn(ExperimentalCoroutinesApi::class)
    val savedScreenings: StateFlow<List<SavedScreening>> = combine(
        _searchQuery,
        _sortOrder,
        _favoritesOnly
    ) { query, sort, favOnly ->
        Triple(query, sort, favOnly)
    }.flatMapLatest { (query, sort, favOnly) ->
        savedScreeningRepository.getSavedScreenings(query, sort, favOnly)
    }.stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())

    fun refreshProjects() {
        viewModelScope.launch {
            try {
                savedScreeningRepository.syncWithBackend()
            } catch (e: Exception) {
                Log.w(TAG, "ProjectsViewModel refresh failed: ${e.message}")
            }
        }
    }

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    fun updateSortOrder(order: SavedScreeningSortOrder) {
        _sortOrder.value = order
    }

    fun toggleFavoritesOnly() {
        _favoritesOnly.value = !_favoritesOnly.value
    }

    fun toggleFavorite(screening: SavedScreening) {
        viewModelScope.launch {
            savedScreeningRepository.toggleFavorite(screening.id)
        }
    }

    fun deleteScreening(screening: SavedScreening) {
        viewModelScope.launch {
            savedScreeningRepository.deleteScreening(screening.id)
        }
    }

    fun renameScreening(screening: SavedScreening, newTitle: String, onResult: (Boolean, String?) -> Unit) {
        viewModelScope.launch {
            val title = newTitle.trim()
            if (title.isBlank()) {
                onResult(false, "Name cannot be empty.")
                return@launch
            }
            val res = savedScreeningRepository.renameScreening(screening.id, title)
            if (res.isSuccess) {
                onResult(true, null)
            } else {
                onResult(false, res.exceptionOrNull()?.message ?: "Failed to rename")
            }
        }
    }

    fun shareScreening(screening: SavedScreening, context: android.content.Context) {
        viewModelScope.launch {
            try {
                val results = screening.scoringResult
                val builder = StringBuilder()
                builder.append("BioPolymer Screening: ${screening.title}\n")
                builder.append("Top Material: ${screening.topMaterialName}\n")
                builder.append("Match Score: ${(screening.topMatchScore * 100).toInt()}%\n")
                if (results.recommendations.isNotEmpty()) {
                    builder.append("\nTop Recommendations:\n")
                    results.recommendations.take(5).forEachIndexed { index, rec ->
                        builder.append("${index + 1}. ${rec.materialName} (${(rec.score * 100).toInt()}% Match)\n")
                    }
                }
                val sendIntent = android.content.Intent().apply {
                    action = android.content.Intent.ACTION_SEND
                    putExtra(android.content.Intent.EXTRA_TEXT, builder.toString())
                    type = "text/plain"
                }
                val shareIntent = android.content.Intent.createChooser(sendIntent, "Share Screening Results")
                context.startActivity(shareIntent)
            } catch (e: Exception) {
                Log.e(TAG, "Error sharing screening", e)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectsScreen(
    onScreeningClick: (SavedScreening) -> Unit,
    viewModel: ProjectsViewModel = hiltViewModel(),
) {
    val context = androidx.compose.ui.platform.LocalContext.current
    val screenings by viewModel.savedScreenings.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val sortOrder by viewModel.sortOrder.collectAsState()
    val favoritesOnly by viewModel.favoritesOnly.collectAsState()

    var showSortMenu by remember { mutableStateOf(false) }
    var screeningToDelete by remember { mutableStateOf<SavedScreening?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Saved Screening Results") },
                actions = {
                    IconButton(onClick = { viewModel.refreshProjects() }) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Refresh Projects")
                    }
                    IconButton(onClick = { viewModel.toggleFavoritesOnly() }) {
                        Icon(
                            imageVector = if (favoritesOnly) Icons.Filled.Star else Icons.Outlined.StarBorder,
                            contentDescription = "Filter Favorites",
                            tint = if (favoritesOnly) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.onSurface
                        )
                    }
                    IconButton(onClick = { showSortMenu = true }) {
                        Icon(Icons.AutoMirrored.Filled.Sort, contentDescription = "Sort")
                    }
                    DropdownMenu(
                        expanded = showSortMenu,
                        onDismissRequest = { showSortMenu = false }
                    ) {
                        SavedScreeningSortOrder.entries.forEach { order ->
                            DropdownMenuItem(
                                text = {
                                    Text(when (order) {
                                        SavedScreeningSortOrder.NEWEST_FIRST -> "Newest First"
                                        SavedScreeningSortOrder.OLDEST_FIRST -> "Oldest First"
                                        SavedScreeningSortOrder.TITLE_ASC -> "Title (A-Z)"
                                        SavedScreeningSortOrder.TITLE_DESC -> "Title (Z-A)"
                                        SavedScreeningSortOrder.MATCH_SCORE_DESC -> "Match Score"
                                    })
                                },
                                onClick = {
                                    viewModel.updateSortOrder(order)
                                    showSortMenu = false
                                },
                                leadingIcon = {
                                    if (sortOrder == order) {
                                        Icon(Icons.Default.Check, contentDescription = null)
                                    }
                                }
                            )
                        }
                    }
                }
            )
        },
    ) { padding ->
        Column(modifier = Modifier.padding(padding)) {
            OutlinedTextField(
                value = searchQuery,
                onValueChange = { viewModel.updateSearchQuery(it) },
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                placeholder = { Text("Search screening results...") },
                leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                trailingIcon = {
                    if (searchQuery.isNotEmpty()) {
                        IconButton(onClick = { viewModel.updateSearchQuery("") }) {
                            Icon(Icons.Default.Close, contentDescription = "Clear")
                        }
                    }
                },
                singleLine = true
            )

            if (screenings.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center,
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                        modifier = Modifier.padding(24.dp)
                    ) {
                        Icon(
                            imageVector = if (searchQuery.isEmpty()) Icons.Filled.FolderOff else Icons.Filled.SearchOff,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp),
                            tint = MaterialTheme.colorScheme.outline
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text(
                            text = if (searchQuery.isEmpty()) "No saved screening results" else "No matching screenings found",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(
                            text = if (searchQuery.isEmpty()) "Run a screening and tap 'Save' to persist your results locally." else "Try adjusting your search terms.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    items(screenings, key = { it.id }) { screening ->
                        SavedScreeningCard(
                            screening = screening,
                            onClick = { onScreeningClick(screening) },
                            onToggleFavorite = { viewModel.toggleFavorite(screening) },
                            onDelete = { screeningToDelete = screening },
                            onRename = { newTitle, onResult ->
                                viewModel.renameScreening(screening, newTitle, onResult)
                            },
                            onShare = { viewModel.shareScreening(screening, context) }
                        )
                    }
                }
            }
        }
    }

    if (screeningToDelete != null) {
        AlertDialog(
            onDismissRequest = { screeningToDelete = null },
            title = { Text("Delete Saved Screening") },
            text = { Text("Are you sure you want to delete '${screeningToDelete?.title}'? This action cannot be undone.") },
            confirmButton = {
                TextButton(
                    onClick = {
                        screeningToDelete?.let { viewModel.deleteScreening(it) }
                        screeningToDelete = null
                    },
                    colors = ButtonDefaults.textButtonColors(contentColor = MaterialTheme.colorScheme.error)
                ) {
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { screeningToDelete = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
fun SavedScreeningCard(
    screening: SavedScreening,
    onClick: () -> Unit,
    onToggleFavorite: () -> Unit,
    onDelete: () -> Unit,
    onRename: (String, (Boolean, String?) -> Unit) -> Unit,
    onShare: () -> Unit
) {
    val dateFormatter = remember { SimpleDateFormat("MMM dd, yyyy • HH:mm", Locale.getDefault()) }
    val dateString = remember(screening.updatedAt) { dateFormatter.format(Date(screening.updatedAt)) }

    var isEditing by remember { mutableStateOf(false) }
    var editTitle by remember { mutableStateOf(screening.title) }
    var editError by remember { mutableStateOf<String?>(null) }

    ElevatedCard(
        modifier = Modifier.fillMaxWidth(),
        onClick = {
            if (!isEditing) {
                onClick()
            }
        }
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header Row: Title, Favorite Icon, Options Menu
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.fillMaxWidth()
            ) {
                Surface(
                    shape = MaterialTheme.shapes.small,
                    color = MaterialTheme.colorScheme.primaryContainer,
                    modifier = Modifier.size(40.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            Icons.Filled.Description,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                }

                Spacer(modifier = Modifier.width(12.dp))

                Column(modifier = Modifier.weight(1f)) {
                    if (isEditing) {
                        OutlinedTextField(
                            value = editTitle,
                            onValueChange = {
                                editTitle = it
                                editError = null
                            },
                            singleLine = true,
                            isError = editError != null,
                            modifier = Modifier.fillMaxWidth()
                        )
                        if (editError != null) {
                            Text(editError!!, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        }
                    } else {
                        Text(
                            text = screening.title,
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = dateString,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                if (isEditing) {
                    IconButton(onClick = {
                        onRename(editTitle) { success, error ->
                            if (success) {
                                isEditing = false
                                editError = null
                            } else {
                                editError = error
                            }
                        }
                    }) {
                        Icon(Icons.Default.Check, contentDescription = "Save", tint = MaterialTheme.colorScheme.primary)
                    }
                    IconButton(onClick = {
                        isEditing = false
                        editTitle = screening.title
                        editError = null
                    }) {
                        Icon(Icons.Default.Close, contentDescription = "Cancel")
                    }
                } else {
                    IconButton(onClick = onToggleFavorite) {
                        Icon(
                            imageVector = if (screening.isFavorite) Icons.Filled.Star else Icons.Outlined.StarBorder,
                            contentDescription = "Favorite",
                            tint = if (screening.isFavorite) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.outline
                        )
                    }

                    var menuExpanded by remember { mutableStateOf(false) }
                    Box {
                        IconButton(onClick = { menuExpanded = true }) {
                            Icon(Icons.Default.MoreVert, contentDescription = "Options")
                        }
                        DropdownMenu(
                            expanded = menuExpanded,
                            onDismissRequest = { menuExpanded = false }
                        ) {
                            DropdownMenuItem(
                                text = { Text("Rename") },
                                onClick = {
                                    menuExpanded = false
                                    isEditing = true
                                },
                                leadingIcon = { Icon(Icons.Default.Edit, contentDescription = null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Share") },
                                onClick = {
                                    menuExpanded = false
                                    onShare()
                                },
                                leadingIcon = { Icon(Icons.Default.Share, contentDescription = null) }
                            )
                            DropdownMenuItem(
                                text = { Text("Delete") },
                                onClick = {
                                    menuExpanded = false
                                    onDelete()
                                },
                                leadingIcon = { Icon(Icons.Default.Delete, contentDescription = null, tint = MaterialTheme.colorScheme.error) }
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))
            HorizontalDivider()
            Spacer(modifier = Modifier.height(12.dp))

            // Body Metrics: Top Material Name, Match Score, Safety Score
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = "Top Match",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.outline
                    )
                    Text(
                        text = screening.topMaterialName.ifBlank { "Screening Result" },
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                }

                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    MetricChip(value = screening.topMatchScore, label = "Match")
                    EvidenceBadge(evidenceLevel = if (screening.safetyScore > 0.6f) "High" else "Med")
                }
            }

            if (screening.summaryText.isNotBlank()) {
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = screening.summaryText,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
