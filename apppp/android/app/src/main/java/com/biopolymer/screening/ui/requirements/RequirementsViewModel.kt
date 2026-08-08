package com.biopolymer.screening.ui.requirements

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.biopolymer.screening.data.local.UserPreferencesRepository
import com.biopolymer.screening.data.local.dao.ProjectDao
import com.biopolymer.screening.data.local.entity.ProjectEntity
import com.biopolymer.screening.data.repository.MaterialRepository
import com.biopolymer.screening.data.repository.SavedScreeningRepository
import com.biopolymer.screening.data.repository.SaveScreeningResult
import com.biopolymer.screening.data.repository.ScreeningRepository
import com.biopolymer.screening.domain.model.*
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.squareup.moshi.Moshi
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

sealed interface RequirementsEvent {
    data object NavigateToResults : RequirementsEvent
}

@HiltViewModel
class RequirementsViewModel @Inject constructor(
    private val screeningRepository: ScreeningRepository,
    private val materialRepository: MaterialRepository,
    private val savedScreeningRepository: SavedScreeningRepository,
    private val scoringEngine: ScoringEngine,
    private val projectDao: ProjectDao,
    private val userPreferencesRepository: UserPreferencesRepository
) : ViewModel() {

    var currentStep by mutableIntStateOf(0)
    val totalSteps: Int = 8

    var mechanical by mutableStateOf(MechanicalReq())
    var barrier by mutableStateOf(BarrierReq())
    var biological by mutableStateOf(BiologicalReq())
    var degradation by mutableStateOf(DegradationReq())
    var processing by mutableStateOf(ProcessingReq())
    var sterilization by mutableStateOf(SterilizationReq())
    var sustainability by mutableStateOf(SustainabilityReq())
    var cost by mutableStateOf(CostReq())

    var activePreset by mutableStateOf<String?>(null)

    private val _showInstructions = MutableStateFlow(false)
    val showInstructions: StateFlow<Boolean> = _showInstructions.asStateFlow()

    private val _results = MutableStateFlow<ScoringEngine.ScoringResult?>(null)
    val results: StateFlow<ScoringEngine.ScoringResult?> = _results.asStateFlow()

    private val _events = MutableSharedFlow<RequirementsEvent>()
    val events: SharedFlow<RequirementsEvent> = _events.asSharedFlow()

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()

    private val _screeningProgressText = MutableStateFlow("Initializing AI Screening Engine...")
    val screeningProgressText: StateFlow<String> = _screeningProgressText.asStateFlow()

    fun nextStep() {
        if (currentStep < totalSteps - 1) {
            currentStep++
        }
    }

    fun previousStep() {
        if (currentStep > 0) {
            currentStep--
        }
    }

    fun applyPreset(preset: String?) {
        activePreset = preset
        when (preset) {
            "Wound Dressing" -> {
                mechanical = MechanicalReq(tensileStrengthMin = 10f, elongationMin = 20f)
                barrier = BarrierReq(wvtrMax = 2000f)
                biological = BiologicalReq(cytotoxicitySafeRequired = true, hemocompatibleRequired = true)
                degradation = DegradationReq(enzymaticRequired = true)
            }
            "Food Packaging" -> {
                mechanical = MechanicalReq(tensileStrengthMin = 25f)
                barrier = BarrierReq(wvtrMax = 50f, otrMax = 100f)
                sustainability = SustainabilityReq(renewableRequired = true, compostableRequired = true)
            }
            "Tissue Engineering" -> {
                biological = BiologicalReq(cytotoxicitySafeRequired = true, hemocompatibleRequired = true)
                degradation = DegradationReq(enzymaticRequired = true, degradationDaysMin = 28, degradationDaysMax = 365)
                sterilization = SterilizationReq(gammaRequired = true)
            }
        }
    }

    fun resetWizard() {
        currentStep = 0
        _results.value = null
        mechanical = MechanicalReq()
        barrier = BarrierReq()
        biological = BiologicalReq()
        degradation = DegradationReq()
        processing = ProcessingReq()
        sterilization = SterilizationReq()
        sustainability = SustainabilityReq()
        cost = CostReq()
        activePreset = null
    }

    fun clearError() {
        _error.value = null
    }

    fun onInstructionsViewed() {
        _showInstructions.value = false
    }

    fun relaxConstraints() {
        biological = biological.copy(cytotoxicitySafeRequired = false, hemocompatibleRequired = false)
        sterilization = sterilization.copy(gammaRequired = false, etoRequired = false, steamRequired = false, uvRequired = false, autoclaveRequired = false)
        processing = processing.copy(filmRequired = false, castingRequired = false, extrusionRequired = false, coatingRequired = false, meltRequired = false)
        runScreening()
    }

    fun buildRequirement(): Requirement {
        return Requirement(
            mechanical = mechanical,
            barrier = barrier,
            biological = biological,
            degradation = degradation,
            processing = processing,
            sterilization = sterilization,
            sustainability = sustainability,
            cost = cost
        )
    }

    fun runScreening() {
        viewModelScope.launch {
            _isLoading.value = true
            _screeningProgressText.value = "Analyzing requirement specifications..."
            try {
                val req = buildRequirement()
                _screeningProgressText.value = "Fetching biopolymer candidate database..."
                val materials = materialRepository.getAllMaterialsSync()
                _screeningProgressText.value = "Running multi-attribute scoring algorithms..."
                val scoringResult = scoringEngine.scoreAndRank(req, materials)
                _results.value = scoringResult
                _events.emit(RequirementsEvent.NavigateToResults)
            } catch (e: Exception) {
                _error.value = e.message ?: "Screening calculation failed"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun saveAsProject(
        title: String,
        overwrite: Boolean = false,
        onSuccess: () -> Unit,
        onDuplicate: (SavedScreening) -> Unit = {},
        onError: (String) -> Unit
    ) {
        viewModelScope.launch {
            try {
                val res = _results.value
                if (res == null) {
                    onError("No screening results available to save")
                    return@launch
                }
                val req = buildRequirement()
                val result = savedScreeningRepository.saveScreening(
                    title = title,
                    requirement = req,
                    scoringResult = res,
                    overwriteIfExists = overwrite
                )
                when (result) {
                    is SaveScreeningResult.Success -> onSuccess()
                    is SaveScreeningResult.DuplicateDetected -> onDuplicate(result.existingScreening)
                    is SaveScreeningResult.Error -> onError(result.message)
                }
            } catch (e: Exception) {
                onError(e.message ?: "Failed to save project")
            }
        }
    }

    fun loadSavedScreening(screening: SavedScreening) {
        val req = screening.requirement
        mechanical = req.mechanical
        barrier = req.barrier
        biological = req.biological
        degradation = req.degradation
        processing = req.processing
        sterilization = req.sterilization
        sustainability = req.sustainability
        cost = req.cost
        
        if (screening.scoringResult.recommendations.isNotEmpty()) {
            _results.value = screening.scoringResult
        } else {
            runScreening()
        }
    }

    fun loadProject(
        project: ProjectEntity,
        onError: (String) -> Unit
    ) {
        viewModelScope.launch {
            try {
                val moshi = Moshi.Builder().build()
                val reqAdapter = moshi.adapter(Requirement::class.java)
                val resAdapter = moshi.adapter(ScoringEngine.ScoringResult::class.java)
                val req = reqAdapter.fromJson(project.requirementsJson)
                if (req != null) {
                    mechanical = req.mechanical
                    barrier = req.barrier
                    biological = req.biological
                    degradation = req.degradation
                    processing = req.processing
                    sterilization = req.sterilization
                    sustainability = req.sustainability
                    cost = req.cost
                }
                if (project.resultsJson.isNotBlank()) {
                    _results.value = resAdapter.fromJson(project.resultsJson)
                }
            } catch (e: Exception) {
                onError(e.message ?: "Failed to load project")
            }
        }
    }
}

