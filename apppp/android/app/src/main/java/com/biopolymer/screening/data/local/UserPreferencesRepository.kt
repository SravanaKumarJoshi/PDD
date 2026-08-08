package com.biopolymer.screening.data.local

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(name = "user_prefs")

data class UserPreferences(
    val darkMode: Boolean = false,
    val offlineMode: Boolean = false,
    val analyticsEnabled: Boolean = true,
    val instructionsViewCount: Int = 0,
    /**
     * Unix-epoch milliseconds of the last *successful* material sync.
     * 0L means the device has never synced — the next sync will be a full
     * catalog fetch (since=1970-01-01T00:00:00Z).
     */
    val lastMaterialSyncMs: Long = 0L,
    /**
     * User-configured custom base URL for the FastAPI backend (e.g., "http://192.168.1.50:8000/").
     * Null means no override is set (the app auto-detects or falls back to BuildConfig.BASE_URL).
     */
    val customBaseUrl: String? = null,
    val lastSuccessfulServerUrl: String? = null,
    val lastConnectedTimeMs: Long = 0L,
    val catalogSeeded: Boolean = false,
)

@Singleton
class UserPreferencesRepository @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val DARK_MODE_KEY = booleanPreferencesKey("dark_mode")
    private val OFFLINE_MODE_KEY = booleanPreferencesKey("offline_mode")
    private val ANALYTICS_ENABLED_KEY = booleanPreferencesKey("analytics_enabled")
    private val INSTRUCTIONS_VIEW_COUNT_KEY = intPreferencesKey("instructions_view_count")
    private val LAST_MATERIAL_SYNC_MS_KEY = longPreferencesKey("last_material_sync_ms")
    private val CUSTOM_BASE_URL_KEY = stringPreferencesKey("custom_base_url")
    private val LAST_SUCCESSFUL_SERVER_URL_KEY = stringPreferencesKey("last_successful_server_url")
    private val LAST_CONNECTED_TIME_MS_KEY = longPreferencesKey("last_connected_time_ms")
    private val CATALOG_SEEDED_KEY = booleanPreferencesKey("catalog_seeded")

    val userPreferencesFlow: Flow<UserPreferences> = context.dataStore.data
        .catch { exception ->
            if (exception is IOException) {
                emit(emptyPreferences())
            } else {
                throw exception
            }
        }
        .map { preferences ->
            UserPreferences(
                darkMode = preferences[DARK_MODE_KEY] ?: false,
                offlineMode = preferences[OFFLINE_MODE_KEY] ?: false,
                analyticsEnabled = preferences[ANALYTICS_ENABLED_KEY] ?: true,
                instructionsViewCount = preferences[INSTRUCTIONS_VIEW_COUNT_KEY] ?: 0,
                lastMaterialSyncMs = preferences[LAST_MATERIAL_SYNC_MS_KEY] ?: 0L,
                customBaseUrl = preferences[CUSTOM_BASE_URL_KEY]?.takeIf { it.isNotBlank() },
                lastSuccessfulServerUrl = preferences[LAST_SUCCESSFUL_SERVER_URL_KEY],
                lastConnectedTimeMs = preferences[LAST_CONNECTED_TIME_MS_KEY] ?: 0L,
                catalogSeeded = preferences[CATALOG_SEEDED_KEY] ?: false,
            )
        }

    // Deprecated, use userPreferencesFlow directly in new code
    val darkModeFlow: Flow<Boolean> = userPreferencesFlow.map { it.darkMode }

    suspend fun setDarkMode(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[DARK_MODE_KEY] = enabled
        }
    }

    suspend fun setOfflineMode(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[OFFLINE_MODE_KEY] = enabled
        }
    }

    suspend fun setAnalyticsEnabled(enabled: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[ANALYTICS_ENABLED_KEY] = enabled
        }
    }

    suspend fun incrementInstructionsViewCount() {
        context.dataStore.edit { preferences ->
            val current = preferences[INSTRUCTIONS_VIEW_COUNT_KEY] ?: 0
            preferences[INSTRUCTIONS_VIEW_COUNT_KEY] = current + 1
        }
    }

    suspend fun setLastMaterialSyncMs(epochMs: Long) {
        context.dataStore.edit { preferences ->
            preferences[LAST_MATERIAL_SYNC_MS_KEY] = epochMs
        }
    }

    suspend fun setCustomBaseUrl(url: String?) {
        context.dataStore.edit { preferences ->
            if (url.isNullOrBlank()) {
                preferences.remove(CUSTOM_BASE_URL_KEY)
            } else {
                preferences[CUSTOM_BASE_URL_KEY] = url.trim()
            }
        }
    }

    suspend fun recordSuccessfulConnection(url: String, epochMs: Long = System.currentTimeMillis()) {
        context.dataStore.edit { preferences ->
            preferences[LAST_SUCCESSFUL_SERVER_URL_KEY] = url
            preferences[LAST_CONNECTED_TIME_MS_KEY] = epochMs
        }
    }

    suspend fun setCatalogSeeded(seeded: Boolean) {
        context.dataStore.edit { preferences ->
            preferences[CATALOG_SEEDED_KEY] = seeded
        }
    }
}
