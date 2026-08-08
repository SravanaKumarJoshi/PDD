package com.biopolymer.screening.data.remote

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import javax.net.ssl.SSLException
import javax.net.ssl.SSLHandshakeException

/**
 * Diagnostic analysis result for a network failure.
 */
data class NetworkDiagnosticReport(
    val category: Category,
    val technicalReason: String,
    val userExplanation: String,
    val recommendedFix: String,
    val targetUrl: String,
) {
    enum class Category {
        NO_INTERNET,
        DNS_FAILURE,
        CONNECTION_REFUSED,
        CONNECT_TIMEOUT,
        READ_TIMEOUT,
        SSL_FAILURE,
        HTTP_CLIENT_ERROR,
        HTTP_SERVER_ERROR,
        UNKNOWN
    }
}

/**
 * Diagnostic engine that inspects low-level exceptions and system network state to determine exact failure cause and actionable remediation steps.
 */
object NetworkDiagnostics {

    fun diagnose(context: Context?, throwable: Throwable, targetUrl: String): NetworkDiagnosticReport {
        // Check active internet connection first
        if (context != null && !isNetworkAvailable(context)) {
            return NetworkDiagnosticReport(
                category = NetworkDiagnosticReport.Category.NO_INTERNET,
                technicalReason = "No active Wi-Fi or Mobile Data network interface enabled on device.",
                userExplanation = "Your device has no active internet or Wi-Fi connection.",
                recommendedFix = "Please enable Wi-Fi or Mobile Data on your device and try again.",
                targetUrl = targetUrl,
            )
        }

        return when {
            throwable is UnknownHostException -> {
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.DNS_FAILURE,
                    technicalReason = "DNS resolution failed for hostname in URL: ${throwable.message}",
                    userExplanation = "Could not resolve the server hostname or IP address.",
                    recommendedFix = "Verify the server URL in Settings -> Server Configuration (ensure host IP format is correct).",
                    targetUrl = targetUrl,
                )
            }
            throwable is ConnectException -> {
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.CONNECTION_REFUSED,
                    technicalReason = "TCP Connection refused at $targetUrl (${throwable.message}). Target port closed or server not listening.",
                    userExplanation = "The server at $targetUrl actively refused the connection.",
                    recommendedFix = "Ensure the FastAPI backend is running (run start_backend.bat) and listening on port 8000.",
                    targetUrl = targetUrl,
                )
            }
            throwable is SocketTimeoutException && (throwable.message?.contains("connect", ignoreCase = true) == true || throwable.message?.contains("failed to connect", ignoreCase = true) == true) -> {
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.CONNECT_TIMEOUT,
                    technicalReason = "TCP Connect Timeout after waiting for response from $targetUrl (${throwable.message}).",
                    userExplanation = "The server at $targetUrl did not respond within the connection timeout window.",
                    recommendedFix = "Check that your phone and PC are connected to the SAME Wi-Fi network, or verify firewall settings on port 8000.",
                    targetUrl = targetUrl,
                )
            }
            throwable is SocketTimeoutException -> {
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.READ_TIMEOUT,
                    technicalReason = "HTTP Read Timeout while waiting for response data from $targetUrl (${throwable.message}).",
                    userExplanation = "The server accepted the request but took too long to complete screening.",
                    recommendedFix = "The backend process may be busy or processing heavy ML calculations. Please try again.",
                    targetUrl = targetUrl,
                )
            }
            throwable is SSLHandshakeException || throwable is SSLException -> {
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.SSL_FAILURE,
                    technicalReason = "SSL/TLS handshake failure: ${throwable.message}",
                    userExplanation = "Could not establish a secure TLS connection with the server.",
                    recommendedFix = "Verify system date/time settings on your device or check server HTTPS configuration.",
                    targetUrl = targetUrl,
                )
            }
            throwable is NetworkException.HttpError -> {
                if (throwable.isServerError) {
                    NetworkDiagnosticReport(
                        category = NetworkDiagnosticReport.Category.HTTP_SERVER_ERROR,
                        technicalReason = "Server returned HTTP ${throwable.httpCode}: ${throwable.apiError?.message}",
                        userExplanation = "The backend server encountered an internal error (HTTP ${throwable.httpCode}).",
                        recommendedFix = "Check backend logs or verify MySQL database connection status.",
                        targetUrl = targetUrl,
                    )
                } else {
                    NetworkDiagnosticReport(
                        category = NetworkDiagnosticReport.Category.HTTP_CLIENT_ERROR,
                        technicalReason = "HTTP Client Error ${throwable.httpCode}: ${throwable.apiError?.message}",
                        userExplanation = throwable.userMessage,
                        recommendedFix = "Check request inputs or requirements configuration.",
                        targetUrl = targetUrl,
                    )
                }
            }
            else -> {
                val msg = throwable.message ?: throwable::class.java.simpleName
                NetworkDiagnosticReport(
                    category = NetworkDiagnosticReport.Category.UNKNOWN,
                    technicalReason = "Unexpected network exception ($msg)",
                    userExplanation = "Unable to connect to server ($msg).",
                    recommendedFix = "Check Settings -> Server Configuration and test your connection.",
                    targetUrl = targetUrl,
                )
            }
        }
    }

    private fun isNetworkAvailable(context: Context): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as? ConnectivityManager ?: return false
        val activeNetwork = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(activeNetwork) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }
}
