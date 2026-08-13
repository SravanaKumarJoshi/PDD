package com.biopolymer.screening.data.repository

import android.content.Context
import android.util.Log
import com.biopolymer.screening.data.local.UserPreferencesRepository
import com.biopolymer.screening.data.remote.ApiErrorBody
import com.biopolymer.screening.data.remote.ApiService
import com.biopolymer.screening.data.remote.ApiResult
import com.biopolymer.screening.data.remote.BaseUrlProvider
import com.biopolymer.screening.data.remote.NetworkDiagnostics
import com.biopolymer.screening.data.remote.NetworkException
import com.biopolymer.screening.data.remote.NetworkMonitor
import com.biopolymer.screening.data.remote.dto.HealthResponseDto
import com.biopolymer.screening.data.remote.dto.ScreeningRequestDto
import com.biopolymer.screening.data.remote.dto.ScreeningResponseDto
import com.squareup.moshi.Moshi
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

private const val TAG = "ScreeningRepository"

@Singleton
class ScreeningRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val apiService: ApiService,
    private val networkMonitor: NetworkMonitor,
    private val baseUrlProvider: BaseUrlProvider,
    private val userPreferencesRepository: UserPreferencesRepository,
    @Named("appMoshi") private val moshi: Moshi,
) {

    suspend fun checkHealth(): ApiResult<HealthResponseDto> = withContext(Dispatchers.IO) {
        val targetUrl = baseUrlProvider.getBaseUrl()
        Log.d(TAG, "checkHealth: Testing server connectivity at $targetUrl")

        if (!networkMonitor.isConnected()) {
            val diag = NetworkDiagnostics.diagnose(context, Exception("No connectivity"), targetUrl)
            return@withContext ApiResult.Error(NetworkException.NoConnectivity(diag.recommendedFix))
        }

        try {
            val response = apiService.healthCheck()
            if (response.isSuccessful && response.body() != null) {
                userPreferencesRepository.recordSuccessfulConnection(targetUrl)
                ApiResult.Success(response.body()!!)
            } else {
                val code = response.code()
                val errorMsg = response.errorBody()?.string() ?: "HTTP $code"
                ApiResult.Error(NetworkException.HttpError(code, ApiErrorBody(message = errorMsg)))
            }
        } catch (e: com.squareup.moshi.JsonDataException) {
            Log.e(TAG, "Health check Moshi JsonDataException: ${e.message}", e)
            ApiResult.Error(NetworkException.ParseError(cause = e, userMessage = "API response schema error: ${e.message}"))
        } catch (e: com.squareup.moshi.JsonEncodingException) {
            Log.e(TAG, "Health check Moshi JsonEncodingException: ${e.message}", e)
            ApiResult.Error(NetworkException.ParseError(cause = e, userMessage = "API response encoding error: ${e.message}"))
        } catch (e: Exception) {
            val diag = NetworkDiagnostics.diagnose(context, e, targetUrl)
            Log.e(TAG, "Health check failed at $targetUrl: ${diag.technicalReason}")
            ApiResult.Error(NetworkException.ConnectionError(e, "${diag.userExplanation}\n${diag.recommendedFix}"))
        }
    }

    suspend fun screenMaterials(requestDto: ScreeningRequestDto): ApiResult<ScreeningResponseDto> =
        withContext(Dispatchers.IO) {
            val targetUrl = baseUrlProvider.getBaseUrl()
            Log.d(TAG, "screenMaterials: Sending screening request to API ($targetUrl): $requestDto")

            if (!networkMonitor.isConnected()) {
                val diag = NetworkDiagnostics.diagnose(context, Exception("No connectivity"), targetUrl)
                Log.e(TAG, "No network connection. ${diag.technicalReason}")
                return@withContext ApiResult.Error(NetworkException.NoConnectivity(diag.recommendedFix))
            }

            try {
                val response = apiService.screenMaterials(requestDto)
                if (response.isSuccessful && response.body() != null) {
                    val body = response.body()!!
                    Log.d(TAG, "screenMaterials: API Call Success! Code=${response.code()}, Total Evaluated=${body.totalEvaluated}, Results=${body.results.size}")
                    userPreferencesRepository.recordSuccessfulConnection(targetUrl)
                    ApiResult.Success(body)
                } else {
                    val errorMsg = response.errorBody()?.string() ?: "HTTP ${response.code()}"
                    Log.e(TAG, "Screening API call failed with code ${response.code()}: $errorMsg")
                    ApiResult.Error(NetworkException.HttpError(response.code(), ApiErrorBody(message = errorMsg)))
                }
            } catch (e: com.squareup.moshi.JsonDataException) {
                Log.e(TAG, "Screening Moshi JsonDataException: ${e.message}", e)
                ApiResult.Error(NetworkException.ParseError(cause = e, userMessage = "API response schema error: ${e.message}"))
            } catch (e: com.squareup.moshi.JsonEncodingException) {
                Log.e(TAG, "Screening Moshi JsonEncodingException: ${e.message}", e)
                ApiResult.Error(NetworkException.ParseError(cause = e, userMessage = "API response encoding error: ${e.message}"))
            } catch (e: Exception) {
                val diag = NetworkDiagnostics.diagnose(context, e, targetUrl)
                Log.e(TAG, "Error executing screening API call: ${diag.technicalReason}", e)
                ApiResult.Error(NetworkException.ConnectionError(e, "${diag.userExplanation}\n\n👉 Suggested Fix: ${diag.recommendedFix}"))
            }
        }
}


