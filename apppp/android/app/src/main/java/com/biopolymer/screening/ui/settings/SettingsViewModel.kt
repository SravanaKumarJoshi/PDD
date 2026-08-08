package com.biopolymer.screening.ui.settings

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.biopolymer.screening.data.local.UserPreferences
import com.biopolymer.screening.data.local.UserPreferencesRepository
import com.biopolymer.screening.data.local.dao.ProjectDao
import com.biopolymer.screening.domain.scoring.ScoringEngine
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import javax.inject.Inject

import com.biopolymer.screening.data.remote.ApiResult
import com.biopolymer.screening.data.remote.BaseUrlProvider
import com.biopolymer.screening.data.remote.ServerDiscoveryEngine
import com.biopolymer.screening.data.repository.ScreeningRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit

private const val TAG = "SettingsVM"

data class ConnectionTestResult(
    val isTesting: Boolean = false,
    val isSuccess: Boolean? = null,
    val message: String? = null,
    val latencyMs: Long? = null,
    val serverInfo: String? = null,
)

data class DiscoveryResult(
    val isScanning: Boolean = false,
    val discoveredUrl: String? = null,
    val statusMessage: String? = null,
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val userPreferencesRepository: UserPreferencesRepository,
    private val baseUrlProvider: BaseUrlProvider,
    private val screeningRepository: ScreeningRepository,
    private val serverDiscoveryEngine: ServerDiscoveryEngine,
    private val auth: FirebaseAuth,
    private val projectDao: ProjectDao,
) : ViewModel() {

    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    // ── Auth ──────────────────────────────────────────────────────────────────

    private val _currentUser = MutableStateFlow<FirebaseUser?>(auth.currentUser)
    val currentUser: StateFlow<FirebaseUser?> = _currentUser.asStateFlow()

    // ── User preferences ──────────────────────────────────────────────────────

    val userPreferences: StateFlow<UserPreferences> = userPreferencesRepository.userPreferencesFlow
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5_000),
            initialValue = UserPreferences(),
        )

    val currentBaseUrl: StateFlow<String> = baseUrlProvider.baseUrlState

    // ── Server Testing & Discovery State ─────────────────────────────────────

    private val _connectionTestResult = MutableStateFlow(ConnectionTestResult())
    val connectionTestResult: StateFlow<ConnectionTestResult> = _connectionTestResult.asStateFlow()

    private val _discoveryResult = MutableStateFlow(DiscoveryResult())
    val discoveryResult: StateFlow<DiscoveryResult> = _discoveryResult.asStateFlow()

    // ── Server Config Actions ────────────────────────────────────────────────

    fun testConnection(inputUrl: String) {
        val normalized = BaseUrlProvider.normalizeUrl(inputUrl)
        if (normalized == null) {
            _connectionTestResult.value = ConnectionTestResult(
                isTesting = false,
                isSuccess = false,
                message = "Invalid URL format. Example: http://192.168.1.50:8000/",
            )
            return
        }

        viewModelScope.launch {
            _connectionTestResult.value = ConnectionTestResult(isTesting = true)
            val startTime = System.currentTimeMillis()

            try {
                val testClient = OkHttpClient.Builder()
                    .connectTimeout(4, TimeUnit.SECONDS)
                    .readTimeout(4, TimeUnit.SECONDS)
                    .build()

                val healthUrl = "${normalized.removeSuffix("/")}/health"
                val request = Request.Builder().url(healthUrl).get().build()

                val (success, message, info) = withContext(Dispatchers.IO) {
                    try {
                        testClient.newCall(request).execute().use { response ->
                            val bodyStr = response.body?.string() ?: ""
                            if (response.isSuccessful && (bodyStr.contains("healthy") || bodyStr.contains("BioPolymer"))) {
                                Triple(true, "Server connection successful! (HTTP ${response.code})", bodyStr)
                            } else {
                                Triple(false, "Server returned HTTP ${response.code}", bodyStr)
                            }
                        }
                    } catch (e: Exception) {
                        val diag = com.biopolymer.screening.data.remote.NetworkDiagnostics.diagnose(null, e, normalized)
                        Triple(false, "${diag.userExplanation}\n${diag.recommendedFix}", null)
                    }
                }

                val latency = System.currentTimeMillis() - startTime
                if (success) {
                    userPreferencesRepository.recordSuccessfulConnection(normalized)
                }

                _connectionTestResult.value = ConnectionTestResult(
                    isTesting = false,
                    isSuccess = success,
                    message = message,
                    latencyMs = latency,
                    serverInfo = info,
                )
            } catch (e: Exception) {
                _connectionTestResult.value = ConnectionTestResult(
                    isTesting = false,
                    isSuccess = false,
                    message = "Test failed: ${e.message}",
                )
            }
        }
    }

    fun saveServerUrl(url: String) {
        val normalized = BaseUrlProvider.normalizeUrl(url) ?: return
        viewModelScope.launch {
            userPreferencesRepository.setCustomBaseUrl(normalized)
            _connectionTestResult.value = ConnectionTestResult(
                isTesting = false,
                isSuccess = true,
                message = "Server URL saved successfully: $normalized",
            )
        }
    }

    fun resetServerUrl() {
        viewModelScope.launch {
            userPreferencesRepository.setCustomBaseUrl(null)
            _connectionTestResult.value = ConnectionTestResult(
                isTesting = false,
                isSuccess = null,
                message = "Reset to default auto-detected URL.",
            )
        }
    }

    fun discoverServer() {
        viewModelScope.launch {
            _discoveryResult.value = DiscoveryResult(isScanning = true, statusMessage = "Scanning local Wi-Fi subnet for port 8000...")
            val foundUrl = serverDiscoveryEngine.discoverLocalServer(8000)
            if (foundUrl != null) {
                _discoveryResult.value = DiscoveryResult(
                    isScanning = false,
                    discoveredUrl = foundUrl,
                    statusMessage = "Discovered BioPolymer server at $foundUrl",
                )
            } else {
                _discoveryResult.value = DiscoveryResult(
                    isScanning = false,
                    discoveredUrl = null,
                    statusMessage = "No active BioPolymer server found on local Wi-Fi.",
                )
            }
        }
    }

    fun clearConnectionTestResult() {
        _connectionTestResult.value = ConnectionTestResult()
    }

    // ── Settings actions ──────────────────────────────────────────────────────

    fun setDarkMode(enabled: Boolean) {
        viewModelScope.launch { userPreferencesRepository.setDarkMode(enabled) }
    }

    fun setOfflineMode(enabled: Boolean) {
        viewModelScope.launch { userPreferencesRepository.setOfflineMode(enabled) }
    }

    fun setAnalyticsEnabled(enabled: Boolean) {
        viewModelScope.launch { userPreferencesRepository.setAnalyticsEnabled(enabled) }
    }

    fun logout(onLogoutSuccess: () -> Unit) {
        auth.signOut()
        _currentUser.value = null
        onLogoutSuccess()
    }

    // ── Data management ───────────────────────────────────────────────────────

    fun deleteAllData(onComplete: () -> Unit) {
        viewModelScope.launch {
            try {
                projectDao.deleteAllProjects()
                Log.i(TAG, "All local saved projects deleted")
                onComplete()
            } catch (e: Exception) {
                Log.e(TAG, "Error deleting saved projects: ${e.message}", e)
                onComplete()
            }
        }
    }

    fun exportData(onResult: (String) -> Unit) {
        viewModelScope.launch {
            try {
                val projects = projectDao.getAllProjectsSync()
                if (projects.isEmpty()) {
                    onResult("No saved projects found.")
                    return@launch
                }

                val resAdapter = moshi.adapter(ScoringEngine.ScoringResult::class.java)
                val dateFormatter = SimpleDateFormat("MMM dd, yyyy HH:mm", Locale.getDefault())

                val builder = StringBuilder()
                builder.append("BioPolymer AI Screening Export\n")
                builder.append("==============================\n\n")

                for (project in projects) {
                    builder.append("Project: ${project.title}\n")
                    builder.append("Date: ${dateFormatter.format(Date(project.updatedAt))}\n\n")

                    val results = try {
                        project.resultsJson?.let { resAdapter.fromJson(it) }
                    } catch (e: Exception) { null }

                    if (results != null && results.recommendations.isNotEmpty()) {
                        builder.append("Top Recommendations:\n")
                        results.recommendations.take(5).forEachIndexed { index, rec ->
                            val category = rec.category.replaceFirstChar {
                                if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString()
                            }
                            builder.append("  ${index + 1}. $category: ${rec.materialName}\n")
                            val scorePct = (rec.score * 100).toInt()
                            val confPct  = (rec.confidence * 100).toInt()
                            builder.append("     Overall Match: $scorePct% (Confidence: $confPct%)\n")
                        }
                    } else {
                        builder.append("No results found for this project.\n\n")
                    }
                    builder.append("------------------------------\n\n")
                }

                onResult(builder.toString().trimEnd())
            } catch (e: Exception) {
                onResult("Error generating export: ${e.message}")
            }
        }
    }
}
