package com.biopolymer.screening.data.remote

/**
 * Sealed hierarchy of typed network errors.
 *
 * Every failure the networking layer can produce is represented here so that
 * call-sites can exhaustively handle each case with a `when` expression
 * instead of catching raw exceptions or inspecting error messages.
 *
 * Design principles:
 *  - No stack-trace details are exposed to the UI layer.
 *  - Each subclass carries only what the UI needs to show a useful message.
 *  - [userMessage] is always safe to display directly to the user.
 */
sealed class NetworkException(
    override val message: String,
    cause: Throwable? = null,
) : Exception(message, cause) {

    /** The device has no active internet connection. */
    class NoConnectivity(
        val userMessage: String = "No internet connection. Please check your network and try again.",
    ) : NetworkException("No network connectivity", cause = null)

    /**
     * The server returned an HTTP error response.
     *
     * @param httpCode  The HTTP status code (e.g. 401, 404, 500).
     * @param apiError  Parsed error body from the server, if available.
     */
    class HttpError(
        val httpCode: Int,
        val apiError: ApiErrorBody? = null,
        cause: Throwable? = null,
    ) : NetworkException("HTTP $httpCode", cause) {

        val userMessage: String get() = when (httpCode) {
            400 -> apiError?.message ?: "The request was invalid. Please try again."
            401 -> "Your session has expired. Please sign in again."
            403 -> "You don't have permission to perform this action."
            404 -> "The requested resource was not found."
            409 -> apiError?.message ?: "A conflict occurred. Please refresh and try again."
            422 -> apiError?.message ?: "The submitted data is invalid."
            429 -> "Too many requests. Please wait a moment and try again."
            in 500..599 -> "A server error occurred. Our team has been notified."
            else -> apiError?.message ?: "An unexpected error occurred (HTTP $httpCode)."
        }

        val isUnauthorized: Boolean get() = httpCode == 401
        val isForbidden: Boolean get() = httpCode == 403
        val isNotFound: Boolean get() = httpCode == 404
        val isServerError: Boolean get() = httpCode in 500..599
        val isRateLimited: Boolean get() = httpCode == 429
    }

    /**
     * A connection-level failure — the request never reached the server.
     * Examples: DNS failure, connection refused, SSL handshake error.
     */
    class ConnectionError(
        cause: Throwable,
        val userMessage: String = "Could not connect to the server. Please check your connection and try again.",
    ) : NetworkException("Connection error: ${cause.message}", cause)

    /**
     * The server took too long to respond.
     *
     * @param isReadTimeout  true = the server started responding but didn't finish;
     *                       false = the initial connection timed out.
     */
    class Timeout(
        val isReadTimeout: Boolean = false,
        cause: Throwable? = null,
        val userMessage: String = "The request timed out. Please try again.",
    ) : NetworkException(if (isReadTimeout) "Read timeout" else "Connect timeout", cause)

    /**
     * The response body could not be parsed into the expected type.
     * This usually indicates an API version mismatch.
     */
    class ParseError(
        cause: Throwable,
        val userMessage: String = "Received an unexpected response. Please update the app.",
    ) : NetworkException("Response parse error: ${cause.message}", cause)

    /** A catch-all for errors that don't fit the categories above. */
    class Unknown(
        cause: Throwable,
        val userMessage: String = "An unexpected error occurred. Please try again.",
    ) : NetworkException("Unknown error: ${cause.message}", cause)
}

/**
 * Error response body returned by the FastAPI backend.
 *
 * Matches the shape produced by the global exception handler in main.py:
 * ```json
 * {
 *   "error": "not_found",
 *   "message": "Material with id X was not found.",
 *   "request_id": "550e8400-..."
 * }
 * ```
 */
data class ApiErrorBody(
    val error: String? = null,
    val message: String? = null,
    val requestId: String? = null,
    val detail: String? = null,       // FastAPI validation error field
)
