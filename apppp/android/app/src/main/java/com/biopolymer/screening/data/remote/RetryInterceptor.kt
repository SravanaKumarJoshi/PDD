package com.biopolymer.screening.data.remote

import android.util.Log
import okhttp3.Interceptor
import okhttp3.Response
import java.io.IOException
import java.net.ConnectException
import java.net.SocketException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "RetryInterceptor"

/**
 * Interceptor that performs automatic exponential backoff retries for transient network connection failures.
 *
 * Rules:
 *  - Retries ONLY connection failures (ConnectException, SocketTimeoutException during connect, DNS failures).
 *  - Does NOT retry HTTP 4xx (validation, auth) or HTTP 5xx responses (handled upstream if needed).
 *  - Backoff delays: Attempt 1 (0ms) -> Attempt 2 (1000ms) -> Attempt 3 (2000ms). Max 3 attempts.
 */
@Singleton
class RetryInterceptor @Inject constructor() : Interceptor {

    private val maxAttempts = 3
    private val initialBackoffMs = 1000L

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request()
        var attempt = 1
        var backoffMs = initialBackoffMs

        while (true) {
            try {
                if (attempt > 1) {
                    Log.i(TAG, "[Attempt $attempt/$maxAttempts] Retrying request ${request.method} ${request.url.encodedPath} after ${backoffMs}ms backoff...")
                    try {
                        Thread.sleep(backoffMs)
                    } catch (ie: InterruptedException) {
                        Thread.currentThread().interrupt()
                        throw IOException("Retry interrupted", ie)
                    }
                    backoffMs *= 2
                }

                val response = chain.proceed(request)
                return response
            } catch (e: IOException) {
                val isRetryable = isTransientConnectionFailure(e)
                if (!isRetryable || attempt >= maxAttempts) {
                    if (isRetryable) {
                        Log.e(TAG, "[Attempt $attempt/$maxAttempts] Network request failed permanently after max retries: ${e::class.java.simpleName}: ${e.message}")
                    } else {
                        Log.d(TAG, "Non-retryable exception: ${e::class.java.simpleName}: ${e.message}")
                    }
                    throw e
                }

                Log.w(TAG, "[Attempt $attempt/$maxAttempts] Transient connection failure (${e::class.java.simpleName}: ${e.message}). Scheduling retry.")
                attempt++
            }
        }
    }

    private fun isTransientConnectionFailure(e: IOException): Boolean {
        return when (e) {
            is ConnectException -> true
            is UnknownHostException -> true
            is SocketTimeoutException -> e.message?.contains("connect", ignoreCase = true) == true || e.message?.contains("timed out", ignoreCase = true) == true
            is SocketException -> true
            else -> e.message?.contains("Failed to connect", ignoreCase = true) == true
        }
    }
}
