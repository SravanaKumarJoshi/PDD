package com.biopolymer.screening.data.remote

import android.util.Log
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "DynamicBaseUrl"

/**
 * OkHttp Interceptor that dynamically updates outgoing request URLs to use the active Base URL from [BaseUrlProvider].
 *
 * This allows changing the server URL at runtime (e.g., in Settings) without needing to re-instantiate Retrofit or ApiService.
 */
@Singleton
class DynamicBaseUrlInterceptor @Inject constructor(
    private val baseUrlProvider: BaseUrlProvider
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()
        val currentBaseUrlStr = baseUrlProvider.getBaseUrl()
        val newBaseHttpUrl = currentBaseUrlStr.toHttpUrlOrNull()

        if (newBaseHttpUrl == null) {
            Log.e(TAG, "Invalid base URL string in BaseUrlProvider: $currentBaseUrlStr")
            return chain.proceed(originalRequest)
        }

        val originalUrl = originalRequest.url

        // Build new URL replacing scheme, host, and port
        val newUrl = originalUrl.newBuilder()
            .scheme(newBaseHttpUrl.scheme)
            .host(newBaseHttpUrl.host)
            .port(newBaseHttpUrl.port)
            .build()

        if (originalUrl.host != newUrl.host || originalUrl.port != newUrl.port || originalUrl.scheme != newUrl.scheme) {
            Log.d(TAG, "Rewriting request URL: ${originalUrl.scheme}://${originalUrl.host}:${originalUrl.port} -> ${newUrl.scheme}://${newUrl.host}:${newUrl.port}")
        }

        val newRequest = originalRequest.newBuilder()
            .url(newUrl)
            .build()

        return chain.proceed(newRequest)
    }
}
