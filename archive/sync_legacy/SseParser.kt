package com.biopolymer.screening.data.sync

import android.util.Log
import com.squareup.moshi.JsonClass
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import com.biopolymer.screening.data.remote.dto.MaterialPropertyDto
import com.biopolymer.screening.data.remote.dto.MaterialResponseDto
import okio.BufferedSource

private const val TAG = "SseParser"

/**
 * Parses raw SSE frames emitted by GET /api/v1/materials/stream.
 *
 * SSE wire format
 * ---------------
 * Each frame is one or more `data: <json>\n` lines followed by a blank line:
 *
 *     data: {"event":"batch","cursor":"...","total":1200,...}\n
 *     \n
 *     data: {"event":"complete","server_timestamp":"...","total_sent":1200}\n
 *     \n
 *
 * Comment lines (`: keepalive\n`) are silently discarded.
 *
 * Usage
 * -----
 * ```kotlin
 * val parser = SseParser(moshi)
 * responseBody.source().use { source ->
 *     parser.parse(source).collect { event ->
 *         when (event) {
 *             is SseEvent.Batch    -> …
 *             is SseEvent.Complete -> …
 *             is SseEvent.Error    -> …
 *         }
 *     }
 * }
 * ```
 */
class SseParser(moshi: Moshi) {

    // ── Adapters ─────────────────────────────────────────────────────────────
    private val envelopeAdapter = moshi.adapter(SseEnvelope::class.java)
    private val batchAdapter    = moshi.adapter(SseBatchPayload::class.java)
    private val completeAdapter = moshi.adapter(SseCompletePayload::class.java)
    private val errorAdapter    = moshi.adapter(SseErrorPayload::class.java)

    /**
     * Read [source] line-by-line, accumulate `data:` lines into frames, and
     * emit parsed [SseEvent] objects.
     *
     * The function is intentionally NOT a Flow so the caller controls
     * suspension and can cancel via its coroutine scope.
     *
     * @throws java.io.IOException on read failures (handled by the caller).
     */
    suspend fun parse(
        source: BufferedSource,
        onEvent: suspend (SseEvent) -> Unit,
    ) {
        val dataAccumulator = StringBuilder()

        while (!source.exhausted()) {
            val line = source.readUtf8Line() ?: break

            when {
                // Comment / keep-alive — discard silently
                line.startsWith(":") -> { /* no-op */ }

                // Data line — accumulate (multi-line data fields are concatenated)
                line.startsWith("data:") -> {
                    val payload = line.removePrefix("data:").trim()
                    dataAccumulator.append(payload)
                }

                // Blank line — dispatch accumulated data as one event
                line.isEmpty() -> {
                    val raw = dataAccumulator.toString().trim()
                    dataAccumulator.clear()
                    if (raw.isNotEmpty()) {
                        parseFrame(raw)?.let { onEvent(it) }
                    }
                }

                // Any other line type (id:, retry:, etc.) — ignore
                else -> {}
            }
        }

        // Handle frames that arrive without a trailing blank line (stream EOF)
        val remaining = dataAccumulator.toString().trim()
        if (remaining.isNotEmpty()) {
            parseFrame(remaining)?.let { onEvent(it) }
        }
    }

    // ── Private frame parser ──────────────────────────────────────────────────

    private fun parseFrame(json: String): SseEvent? {
        return try {
            val envelope = envelopeAdapter.fromJson(json)
                ?: return logAndNull("Null envelope for frame")

            when (envelope.event) {
                "batch" -> {
                    val batch = batchAdapter.fromJson(json)
                        ?: return logAndNull("Null batch payload")
                    SseEvent.Batch(
                        cursor     = batch.cursor,
                        total      = batch.total,
                        offset     = batch.offset,
                        count      = batch.count,
                        materials  = batch.materials,
                    )
                }
                "complete" -> {
                    val complete = completeAdapter.fromJson(json)
                        ?: return logAndNull("Null complete payload")
                    SseEvent.Complete(
                        serverTimestamp = complete.serverTimestamp,
                        totalSent       = complete.totalSent,
                        deletedIds      = complete.deletedIds,
                    )
                }
                "error" -> {
                    val error = errorAdapter.fromJson(json)
                        ?: return logAndNull("Null error payload")
                    SseEvent.ServerError(
                        code      = error.code,
                        message   = error.message,
                        retryable = error.retryable,
                    )
                }
                else -> {
                    Log.w(TAG, "Unknown SSE event type: '${envelope.event}' — skipping")
                    null
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse SSE frame: ${e.message}\nRaw: $json", e)
            null
        }
    }

    private fun logAndNull(reason: String): SseEvent? {
        Log.w(TAG, reason)
        return null
    }
}

// ── Sealed event hierarchy ────────────────────────────────────────────────────

/** Typed SSE event emitted by [SseParser]. */
sealed interface SseEvent {

    /** A batch of materials arriving mid-stream. */
    data class Batch(
        val cursor: String,
        val total: Int,
        val offset: Int,
        val count: Int,
        val materials: List<MaterialResponseDto>,
    ) : SseEvent

    /** The server has finished streaming all matching rows. */
    data class Complete(
        val serverTimestamp: String,
        val totalSent: Int,
        val deletedIds: List<String>,
    ) : SseEvent

    /** The server signalled an error mid-stream. */
    data class ServerError(
        val code: String,
        val message: String,
        val retryable: Boolean,
    ) : SseEvent
}

// ── Internal Moshi DTOs for SSE frame deserialization ────────────────────────
// These are private to this parser — external code uses [SseEvent] only.

/** Minimal envelope to peek at the event type before full deserialization. */
@JsonClass(generateAdapter = true)
internal data class SseEnvelope(
    val event: String = "",
)

@JsonClass(generateAdapter = true)
internal data class SseBatchPayload(
    val event: String = "batch",
    val cursor: String = "",
    val total: Int = 0,
    val offset: Int = 0,
    val count: Int = 0,
    val materials: List<MaterialResponseDto> = emptyList(),
)

@JsonClass(generateAdapter = true)
internal data class SseCompletePayload(
    val event: String = "complete",
    @com.squareup.moshi.Json(name = "server_timestamp")
    val serverTimestamp: String = "",
    @com.squareup.moshi.Json(name = "total_sent")
    val totalSent: Int = 0,
    @com.squareup.moshi.Json(name = "deleted_ids")
    val deletedIds: List<String> = emptyList(),
)

@JsonClass(generateAdapter = true)
internal data class SseErrorPayload(
    val event: String = "error",
    val code: String = "",
    val message: String = "",
    val retryable: Boolean = true,
)
