package com.biopolymer.screening.data.remote

import android.util.Log
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.ResponseBody
import retrofit2.HttpException
import retrofit2.Response
import java.io.InterruptedIOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException
import javax.net.ssl.SSLHandshakeException

private const val TAG = "safeApiCall"

/**
 * Executes a suspend [block] that returns a [Response]<T> and maps the
 * outcome to [ApiResult]<T>.
 *
 * Error mapping:
 *
 * | Throwable / HTTP status        | [ApiResult] produced                    |
 * |--------------------------------|-----------------------------------------|
 * | [UnknownHostException]         | Error(NoConnectivity)                   |
 * | [ConnectException]             | Error(ConnectionError)                  |
 * | [SocketTimeoutException]       | Error(Timeout)                          |
 * | [InterruptedIOException]       | Error(Timeout)                          |
 * | [SSLException] / [SSLHandshake]| Error(ConnectionError) — TLS failure    |
 * | HTTP 4xx / 5xx                 | Error(HttpError) with parsed body       |
 * | JSON parse failure             | Error(ParseError)                       |
 * | Everything else                | Error(Unknown)                          |
 * | HTTP 2xx                       | Success(data)                           |
 *
 * Usage:
 * ```kotlin
 * suspend fun getMaterials(): ApiResult<List<Material>> = safeApiCall {
 *     apiService.getMaterials()
 * }
 * ```
 *
 * The [networkMonitor] overload checks connectivity before making the call
 * and short-circuits with [NetworkException.NoConnectivity] if offline:
 * ```kotlin
 * suspend fun getMaterials(): ApiResult<List<Material>> =
 *     safeApiCall(networkMonitor) { apiService.getMaterials() }
 * ```
 */
suspend fun <T> safeApiCall(
    networkMonitor: NetworkMonitor? = null,
    block: suspend () -> Response<T>,
): ApiResult<T> {
    // --- Pre-flight connectivity check ---
    if (networkMonitor != null && !networkMonitor.isConnected()) {
        Log.d(TAG, "Skipping API call — no network connectivity")
        return ApiResult.Error(NetworkException.NoConnectivity())
    }

    return try {
        val response = block()
        if (response.isSuccessful) {
            val body = response.body()
            if (body != null) {
                ApiResult.Success(body)
            } else {
                // 204 No Content or unexpectedly null body on a 2xx response
                @Suppress("UNCHECKED_CAST")
                ApiResult.Success(Unit as T)
            }
        } else {
            val errorBody = parseErrorBody(response.errorBody())
            Log.w(TAG, "HTTP ${response.code()} — ${errorBody?.message ?: "no body"}")
            ApiResult.Error(
                NetworkException.HttpError(
                    httpCode = response.code(),
                    apiError = errorBody,
                )
            )
        }
    } catch (e: UnknownHostException) {
        // DNS resolution failed — almost always means no internet.
        Log.w(TAG, "UnknownHostException: ${e.message}")
        ApiResult.Error(NetworkException.NoConnectivity())
    } catch (e: ConnectException) {
        Log.w(TAG, "ConnectException: ${e.message}")
        ApiResult.Error(NetworkException.ConnectionError(cause = e))
    } catch (e: SocketTimeoutException) {
        Log.w(TAG, "SocketTimeoutException: ${e.message}")
        ApiResult.Error(
            NetworkException.Timeout(
                isReadTimeout = e.message?.contains("Read timed out", ignoreCase = true) == true,
                cause = e,
            )
        )
    } catch (e: InterruptedIOException) {
        // OkHttp throws this for call timeouts (callTimeout exceeded).
        Log.w(TAG, "InterruptedIOException (call timeout): ${e.message}")
        ApiResult.Error(NetworkException.Timeout(cause = e))
    } catch (e: SSLHandshakeException) {
        Log.e(TAG, "SSLHandshakeException: ${e.message}")
        ApiResult.Error(
            NetworkException.ConnectionError(
                cause = e,
                userMessage = "A secure connection could not be established. " +
                    "Please ensure your device date/time is correct and try again.",
            )
        )
    } catch (e: SSLException) {
        Log.e(TAG, "SSLException: ${e.message}")
        ApiResult.Error(NetworkException.ConnectionError(cause = e))
    } catch (e: HttpException) {
        // Retrofit wraps HTTP error responses as HttpException when the
        // return type is NOT Response<T>.  With Response<T> we handle errors
        // above, but guard here in case raw calls slip through.
        Log.w(TAG, "HttpException: ${e.code()} ${e.message()}")
        ApiResult.Error(
            NetworkException.HttpError(
                httpCode = e.code(),
                cause = e,
            )
        )
    } catch (e: com.squareup.moshi.JsonDataException) {
        Log.e(TAG, "JsonDataException (parse error): ${e.message}")
        ApiResult.Error(NetworkException.ParseError(cause = e))
    } catch (e: com.squareup.moshi.JsonEncodingException) {
        Log.e(TAG, "JsonEncodingException (parse error): ${e.message}")
        ApiResult.Error(NetworkException.ParseError(cause = e))
    } catch (e: Exception) {
        Log.e(TAG, "Unexpected exception during API call: ${e.message}", e)
        ApiResult.Error(NetworkException.Unknown(cause = e))
    }
}

// ---------------------------------------------------------------------------
// Error body parser
// ---------------------------------------------------------------------------

/**
 * Attempts to parse the error [ResponseBody] from the server into an
 * [ApiErrorBody].  Returns null if the body is empty or cannot be parsed —
 * callers fall back to generic status-code messages in that case.
 */
private val errorBodyMoshi: Moshi = Moshi.Builder()
    .add(KotlinJsonAdapterFactory())
    .build()

private fun parseErrorBody(body: ResponseBody?): ApiErrorBody? {
    if (body == null) return null
    return try {
        val json = body.string()
        if (json.isBlank()) return null
        errorBodyMoshi
            .adapter(ApiErrorBody::class.java)
            .fromJson(json)
    } catch (e: Exception) {
        Log.d(TAG, "Could not parse error body: ${e.message}")
        null
    }
}

// ---------------------------------------------------------------------------
// ViewModel helpers
// ---------------------------------------------------------------------------

/**
 * Returns a safe, user-facing message from any [NetworkException] subtype.
 *
 * Centralises the mapping so UI code never needs to import or switch on
 * [NetworkException] subclasses directly.
 */
val NetworkException.userMessage: String
    get() = when (this) {
        is NetworkException.NoConnectivity  -> userMessage
        is NetworkException.HttpError       -> userMessage
        is NetworkException.ConnectionError -> userMessage
        is NetworkException.Timeout         -> userMessage
        is NetworkException.ParseError      -> userMessage
        is NetworkException.Unknown         -> userMessage
    }

/**
 * Returns true if this [ApiResult.Error] represents a 401 Unauthorized,
 * which should trigger a sign-out flow in the ViewModel.
 */
fun ApiResult<*>.isUnauthorized(): Boolean =
    this is ApiResult.Error &&
        exception is NetworkException.HttpError &&
        (exception as NetworkException.HttpError).isUnauthorized
