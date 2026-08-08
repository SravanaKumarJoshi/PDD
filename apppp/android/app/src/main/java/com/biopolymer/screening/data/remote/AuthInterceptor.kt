package com.biopolymer.screening.data.remote

import android.util.Log
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.tasks.await
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "AuthInterceptor"
private const val HEADER_AUTHORIZATION = "Authorization"
private const val HEADER_REQUEST_ID = "X-Request-ID"

/**
 * OkHttp [Interceptor] that attaches a Firebase ID token to every outgoing
 * request as a Bearer token.
 *
 * Behaviour:
 *  - If the user is signed in, a fresh (or cached) Firebase ID token is
 *    fetched synchronously and appended as `Authorization: Bearer <token>`.
 *  - Tokens are refreshed automatically by the Firebase SDK when they expire
 *    (every hour).  Passing `forceRefresh = false` returns the cached token
 *    when it is still valid, avoiding an unnecessary network round-trip.
 *  - If the user is NOT signed in (e.g. on the login screen) the request
 *    proceeds without an Authorization header — unauthenticated endpoints
 *    such as GET /api/v1/materials still work.
 *  - On a 401 response the token is force-refreshed once and the request is
 *    retried.  If the retry also returns 401 the response is returned as-is
 *    so the ViewModel can sign the user out via the [NetworkException.HttpError]
 *    path.
 *  - A unique [HEADER_REQUEST_ID] (UUID) is added to every request so that
 *    server logs and client logs can be correlated.
 *
 * Thread safety: [runBlocking] is intentional here because OkHttp interceptors
 * run on a background thread from OkHttp's dispatcher — blocking that thread
 * is safe and expected.
 */
@Singleton
class AuthInterceptor @Inject constructor(
    private val firebaseAuth: FirebaseAuth,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val originalRequest = chain.request()

        // Preserve an ID supplied by the caller; otherwise create one.  This
        // keeps ViewModel, OkHttp, and FastAPI logs on one trace ID.
        val requestId = originalRequest.header(HEADER_REQUEST_ID)
            ?: java.util.UUID.randomUUID().toString()

        val requestWithId = originalRequest.newBuilder()
            .header(HEADER_REQUEST_ID, requestId)
            .build()

        val token = fetchToken(forceRefresh = false)

        val authenticatedRequest = if (token != null) {
            requestWithId.newBuilder()
                .header(HEADER_AUTHORIZATION, "Bearer $token")
                .build()
        } else {
            requestWithId
        }

        val response = chain.proceed(authenticatedRequest)

        // 401: token may have expired between the SDK's cache and the server.
        // Force-refresh once and retry before giving up.
        if (response.code == 401 && token != null) {
            Log.d(TAG, "Received 401 — force-refreshing Firebase token and retrying")
            response.close()

            val freshToken = fetchToken(forceRefresh = true)
            val retryRequest = if (freshToken != null) {
                authenticatedRequest.newBuilder()
                    .header(HEADER_AUTHORIZATION, "Bearer $freshToken")
                    .build()
            } else {
                authenticatedRequest
            }
            return chain.proceed(retryRequest)
        }

        return response
    }

    /**
     * Fetches the current user's Firebase ID token.
     *
     * @param forceRefresh  When true, bypasses the local cache and contacts
     *                      Firebase servers to obtain a freshly signed token.
     * @return              The ID token string, or null if no user is signed in
     *                      or the token fetch failed.
     */
    private fun fetchToken(forceRefresh: Boolean): String? {
        val user = firebaseAuth.currentUser ?: return null
        return try {
            runBlocking {
                user.getIdToken(forceRefresh).await().token
            }
        } catch (e: Exception) {
            Log.w(TAG, "Failed to fetch Firebase ID token: ${e.message}")
            null
        }
    }
}
