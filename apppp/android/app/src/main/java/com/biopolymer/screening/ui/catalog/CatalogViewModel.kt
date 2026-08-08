package com.biopolymer.screening.ui.catalog

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.biopolymer.screening.data.repository.MaterialRepository
import com.biopolymer.screening.domain.model.MaterialCardModel
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.*
import javax.inject.Inject

@HiltViewModel
class CatalogViewModel @Inject constructor(
    private val materialRepository: MaterialRepository,
) : ViewModel() {

    val searchQuery = MutableStateFlow("")
    val selectedCategory = MutableStateFlow<String?>(null)

    val categories: StateFlow<List<String>> = materialRepository.getCategories()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    @OptIn(ExperimentalCoroutinesApi::class)
    val materials: StateFlow<List<MaterialCardModel>> = combine(searchQuery, selectedCategory) { query, category ->
        Pair(query.trim(), category)
    }.flatMapLatest { (query, category) ->
        when {
            query.isNotBlank() -> materialRepository.searchMaterialCards(query)
            category != null -> materialRepository.getMaterialCardsByCategory(category)
            else -> materialRepository.getMaterialCards()
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun onSearchQueryChanged(query: String) {
        searchQuery.value = query
    }

    fun onCategorySelected(category: String?) {
        selectedCategory.value = category
    }
}
