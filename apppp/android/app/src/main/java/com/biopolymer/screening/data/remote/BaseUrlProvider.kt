package com.biopolymer.screening.data.remote

import android.os.Build
import android.util.Log
import com.biopolymer.screening.BuildConfig
import com.biopolymer.screening.data.local.UserPreferencesRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "BaseUrlProvider"

/**
 * Encapsulates Android hardware build properties for deterministic emulator detection and unit testing.
 */
data class DeviceBuildInfo(
    val fingerprint: String = try { Build.FINGERPRINT ?: "" } catch (e: Throwable) { "" },
    val model: String = try { Build.MODEL ?: "" } catch (e: Throwable) { "" },
    val manufacturer: String = try { Build.MANUFACTURER ?: "" } catch (e: Throwable) { "" },
    val hardware: String = try { Build.HARDWARE ?: "" } catch (e: Throwable) { "" },
    val brand: String = try { Build.BRAND ?: "" } catch (e: Throwable) { "" },
    val device: String = try { Build.DEVICE ?: "" } catch (e: Throwable) { "" },
    val product: String = try { Build.PRODUCT ?: "" } catch (e: Throwable) { "" },
    val board: String = try { Build.BOARD ?: "" } catch (e: Throwable) { "" },
)

@Singleton
class BaseUrlProvider @Inject constructor(
    private val userPreferencesRepository: UserPreferencesRepository,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val _baseUrlState = MutableStateFlow(resolveInitialUrl())
    val baseUrlState: StateFlow<String> = _baseUrlState.asStateFlow()

    init {
        scope.launch {
            userPreferencesRepository.userPreferencesFlow.collectLatest { prefs ->
                val resolved = resolveEffectiveUrl(
                    customUrl = prefs.customBaseUrl,
                    lastSuccessfulUrl = prefs.lastSuccessfulServerUrl
                )
                if (_baseUrlState.value != resolved) {
                    Log.i(TAG, "Base URL updated from DataStore: $resolved")
                    _baseUrlState.value = resolved
                }
            }
        }
    }

    /**
     * Returns the currently active normalized base URL string.
     */
    fun getBaseUrl(): String = _baseUrlState.value

    /**
     * Resolves the effective Base URL following physical device safety rules:
     * 1. User-saved custom Base URL from DataStore
     * 2. Android Emulator loopback (http://10.0.2.2:8000/) ONLY on confirmed emulators
     * 3. Physical Devices NEVER receive 10.0.2.2. If 10.0.2.2 is configured, it is converted
     *    to last successful URL or http://127.0.0.1:8000/ (for adb reverse USB debugging).
     */
    fun resolveEffectiveUrl(
        customUrl: String?,
        lastSuccessfulUrl: String? = null,
        buildInfo: DeviceBuildInfo = currentDeviceBuildInfo()
    ): String {
        val isEmu = isEmulator(buildInfo)
        val deviceTypeStr = if (isEmu) "Android Emulator (AVD)" else "Physical Device"

        // 1. User Custom Override
        if (!customUrl.isNullOrBlank()) {
            val normalized = normalizeUrl(customUrl)
            if (normalized != null) {
                val sanitized = if (!isEmu && normalized.contains("10.0.2.2")) {
                    val safeUrl = normalized.replace("10.0.2.2", "127.0.0.1")
                    safeLogWarn(TAG, "[DEVICE DETECTION] $deviceTypeStr detected with 10.0.2.2 URL. 10.0.2.2 is unreachable on physical devices. Auto-converting $normalized -> $safeUrl")
                    safeUrl
                } else {
                    normalized
                }
                safeLogInfo(TAG, "[DEVICE DETECTION]\n" +
                        "  • Device Type : $deviceTypeStr\n" +
                        "  • Selected URL: $sanitized\n" +
                        "  • Reason      : User-configured custom URL in Settings")
                return sanitized
            }
        }

        // 2. Default BuildConfig BASE_URL resolution
        var candidateUrl = BuildConfig.BASE_URL.trim()
        if (!candidateUrl.endsWith("/")) candidateUrl += "/"

        val selectedUrl: String
        val selectionReason: String

        if (isEmu) {
            // Android Emulator (AVD)
            if (candidateUrl.contains("127.0.0.1") || candidateUrl.contains("localhost")) {
                selectedUrl = candidateUrl.replace("127.0.0.1", "10.0.2.2").replace("localhost", "10.0.2.2")
                selectionReason = "Android Emulator detected. Transformed localhost/127.0.0.1 to AVD loopback 10.0.2.2"
            } else {
                selectedUrl = normalizeUrl(candidateUrl) ?: "http://10.0.2.2:8000/"
                selectionReason = "Android Emulator detected. Using BuildConfig or default AVD loopback 10.0.2.2"
            }
        } else {
            // Physical Device (Must NEVER return 10.0.2.2)
            if (candidateUrl.contains("10.0.2.2")) {
                if (!lastSuccessfulUrl.isNullOrBlank()) {
                    val normLast = normalizeUrl(lastSuccessfulUrl)
                    if (normLast != null && !normLast.contains("10.0.2.2")) {
                        selectedUrl = normLast
                        selectionReason = "Physical Device detected. Replaced unreachable 10.0.2.2 with last working server URL ($normLast)"
                    } else {
                        selectedUrl = "http://127.0.0.1:8000/"
                        selectionReason = "Physical Device detected. Replaced unreachable emulator loopback 10.0.2.2 with 127.0.0.1 (USB debugging / adb reverse baseline)"
                    }
                } else {
                    selectedUrl = "http://127.0.0.1:8000/"
                    selectionReason = "Physical Device detected. Replaced unreachable emulator loopback 10.0.2.2 with 127.0.0.1 (USB debugging / adb reverse baseline)"
                }
            } else {
                selectedUrl = normalizeUrl(candidateUrl) ?: "http://127.0.0.1:8000/"
                selectionReason = "Physical Device detected. Using configured production/LAN Base URL"
            }
        }

        safeLogInfo(TAG, "[DEVICE DETECTION]\n" +
                "  • Device Type : $deviceTypeStr\n" +
                "  • Model/Fingerprint: ${buildInfo.model} / ${buildInfo.fingerprint}\n" +
                "  • Input URL   : $candidateUrl\n" +
                "  • Selected URL: $selectedUrl\n" +
                "  • Reason      : $selectionReason")

        return selectedUrl
    }

    private fun resolveInitialUrl(): String {
        return resolveEffectiveUrl(null)
    }

    companion object {
        fun currentDeviceBuildInfo(): DeviceBuildInfo = DeviceBuildInfo()

        fun isEmulator(info: DeviceBuildInfo = currentDeviceBuildInfo()): Boolean {
            val fingerprint = info.fingerprint.lowercase()
            val model = info.model.lowercase()
            val manufacturer = info.manufacturer.lowercase()
            val hardware = info.hardware.lowercase()
            val brand = info.brand.lowercase()
            val device = info.device.lowercase()
            val product = info.product.lowercase()
            val board = info.board.lowercase()

            return (fingerprint.startsWith("generic")
                    || fingerprint.startsWith("unknown")
                    || model.contains("google_sdk")
                    || model.contains("emulator")
                    || model.contains("android sdk built for x86")
                    || model.contains("sdk_gphone")
                    || manufacturer.contains("genymotion")
                    || (manufacturer.contains("google") && model.contains("sdk"))
                    || hardware.contains("goldfish")
                    || hardware.contains("ranchu")
                    || hardware.contains("vbox86")
                    || (brand.startsWith("generic") && device.startsWith("generic"))
                    || "google_sdk" == product
                    || product.contains("sdk_gphone")
                    || product.contains("vbox86p")
                    || product.contains("emulator")
                    || product.contains("simulator")
                    || board.contains("goldfish"))
        }

        fun normalizeUrl(rawUrl: String): String? {
            var trimmed = rawUrl.trim()
            if (trimmed.isEmpty()) return null

            if (!trimmed.startsWith("http://") && !trimmed.startsWith("https://")) {
                trimmed = "http://$trimmed"
            }

            if (!trimmed.endsWith("/")) {
                trimmed += "/"
            }

            val httpUrl = trimmed.toHttpUrlOrNull() ?: return null
            return httpUrl.toString()
        }

        fun safeLogInfo(tag: String, message: String) {
            try {
                Log.i(tag, message)
            } catch (e: Throwable) {
                println("INFO: [$tag] $message")
            }
        }

        fun safeLogWarn(tag: String, message: String) {
            try {
                Log.w(tag, message)
            } catch (e: Throwable) {
                println("WARN: [$tag] $message")
            }
        }
    }
}
