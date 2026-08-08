package com.biopolymer.screening.data.sync

/**
 * Complete sealed hierarchy describing every state the sync engine can be in.
 *
 * Design principles
 * -----------------
 * - Every state is immutable and carries exactly the data the UI needs.
 * - [Streaming] carries a [SyncProgress] snapshot so the UI can render a
 *   live progress bar without polling.
 * - [Failed] carries a [SyncError] so the UI can distinguish transient
 *   failures (show retry) from permanent ones (show error screen).
 * - [Idle] is the initial state on a fresh install. Once [Completed] is
 *   received the ViewModel should transition back to [Idle] after a short
 *   display delay so the UI does not permanently show "last sync time".
 *
 * State machine
 * -------------
 *
 *   Idle ──────────────────────────────────────────► Connecting
 *                                                        │
 *                                          ┌────────────▼────────────┐
 *                                          │       Streaming         │
 *                                          │  (repeats per batch)    │
 *                                          └────────────┬────────────┘
 *                                                       │
 *                                      ┌────────────────┼────────────────┐
 *                                      ▼                ▼                ▼
 *                                  Completed         Failed           Retrying
 *                                      │                │                │
 *                                      ▼                ▼                ▼
 *                                    Idle            Idle          Connecting
 */
sealed interface SyncState {

    /** No sync is running. The catalog is either empty or from a previous sync. */
    data object Idle : SyncState

    /** Establishing the SSE connection to the server. */
    data object Connecting : SyncState

    /**
     * The SSE stream is open and batches are arriving.
     *
     * @param progress Live progress snapshot — updated after every batch.
     */
    data class Streaming(val progress: SyncProgress) : SyncState

    /**
     * All batches have been received and committed to Room.
     *
     * @param inserted   Number of new materials written to Room.
     * @param updated    Number of existing materials updated in Room.
     * @param deleted    Number of materials soft-deleted locally.
     * @param durationMs Wall-clock time for the entire sync in milliseconds.
     * @param isFirstSync True when this was the initial full-catalog download.
     */
    data class Completed(
        val inserted: Int,
        val updated: Int,
        val deleted: Int,
        val durationMs: Long,
        val isFirstSync: Boolean,
    ) : SyncState

    /**
     * The sync failed and will not retry automatically.
     *
     * WorkManager retries with exponential backoff are separate from this
     * flag — this represents a terminal failure for the *current* attempt.
     *
     * @param error   Typed error descriptor.
     * @param attempt The attempt number (1 = first try).
     */
    data class Failed(
        val error: SyncError,
        val attempt: Int = 1,
    ) : SyncState

    /**
     * A transient error occurred; the engine is waiting before the next
     * automatic retry.
     *
     * @param attempt    Which attempt just failed (1-indexed).
     * @param maxAttempts Total number of attempts before giving up.
     * @param delayMs    How long (ms) before the next attempt.
     * @param cause      The error that triggered this retry.
     */
    data class Retrying(
        val attempt: Int,
        val maxAttempts: Int,
        val delayMs: Long,
        val cause: SyncError,
    ) : SyncState
}


/**
 * Live progress snapshot emitted during [SyncState.Streaming].
 *
 * @param totalMaterials  Total number of rows the server will stream.
 *                        0 if the server has not sent the total yet.
 * @param receivedMaterials  Materials received and committed so far.
 * @param currentBatch    1-indexed batch counter.
 * @param isFirstSync     True when [receivedMaterials] starts from 0
 *                        (the device has never synced before).
 * @param insertedSoFar   Room inserts performed so far.
 * @param updatedSoFar    Room updates performed so far.
 * @param elapsedMs       Wall-clock time since sync started.
 */
data class SyncProgress(
    val totalMaterials: Int = 0,
    val receivedMaterials: Int = 0,
    val currentBatch: Int = 0,
    val isFirstSync: Boolean = false,
    val insertedSoFar: Int = 0,
    val updatedSoFar: Int = 0,
    val elapsedMs: Long = 0L,
) {
    /** Fractional progress 0.0..1.0, or -1f when the total is unknown. */
    val fraction: Float
        get() = if (totalMaterials > 0)
            (receivedMaterials.toFloat() / totalMaterials).coerceIn(0f, 1f)
        else -1f

    /** Human-readable percentage string, e.g. "34%" or "…" when unknown. */
    val percentText: String
        get() = if (totalMaterials > 0) "${(fraction * 100).toInt()}%" else "…"
}


/**
 * Typed error descriptor carried by [SyncState.Failed] and [SyncState.Retrying].
 */
sealed interface SyncError {

    /** The device has no internet access. */
    data object NoConnectivity : SyncError

    /** The server did not respond within the configured timeout. */
    data class Timeout(val isReadTimeout: Boolean = false) : SyncError

    /** A transient server error (5xx). Retrying may succeed. */
    data class ServerError(val httpCode: Int) : SyncError

    /** An authentication or authorisation failure (401/403). */
    data class AuthError(val httpCode: Int) : SyncError

    /** The SSE stream was interrupted (client disconnect, proxy reset, etc.). */
    data class StreamInterrupted(val cause: String) : SyncError

    /** A batch could not be parsed or written to Room. */
    data class DataError(val cause: String) : SyncError

    /** Device storage is too low to write new rows. */
    data object LowStorage : SyncError

    /** A catch-all for errors that don't map to a specific type above. */
    data class Unknown(val cause: String) : SyncError

    /** Returns true if it makes sense to retry this error automatically. */
    val isRetryable: Boolean
        get() = when (this) {
            is NoConnectivity    -> true
            is Timeout           -> true
            is ServerError       -> httpCode in 500..599
            is StreamInterrupted -> true
            is AuthError         -> false
            is DataError         -> false
            is LowStorage        -> false
            is Unknown           -> false
        }

    /** Safe user-facing message. Never exposes internal details. */
    val userMessage: String
        get() = when (this) {
            is NoConnectivity    -> "No internet connection. Sync will resume automatically."
            is Timeout           -> "Server took too long to respond. Will retry shortly."
            is ServerError       -> "Server error ($httpCode). Will retry shortly."
            is AuthError         -> "Authentication failed. Please sign in again."
            is StreamInterrupted -> "Connection interrupted. Will resume from last checkpoint."
            is DataError         -> "Could not save materials. Please try again."
            is LowStorage        -> "Not enough storage space to sync materials."
            is Unknown           -> "An unexpected error occurred. Will retry shortly."
        }
}
