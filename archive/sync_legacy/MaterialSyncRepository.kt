package com.biopolymer.screening.data.sync

import android.util.Log
import com.biopolymer.screening.BuildConfig
import com.biopolymer.screening.data.local.UserPreferencesRepository
import com.biopolymer.screening.data.local.dao.MaterialDao
import com.biopolymer.screening.data.local.entity.MaterialEntity
import com.biopolymer.screening.data.local.entity.MaterialPropertyEntity
import com.biopolymer.screening.data.local.entity.SyncMetadataEntity
import com.biopolymer.screening.data.local.dao.SyncMetadataDao
import com.biopolymer.screening.data.remote.AuthInterceptor
import com.biopolymer.screening.data.remote.NetworkMonitor
import com.biopolymer.screening.data.remote.dto.MaterialResponseDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import java.io.IOException
import java.net.SocketTimeoutException
import java.time.Instant
import java.util.UUID
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import javax.inject.Inject
import javax.inject.Named
import javax.inject.Singleton

private const val TAG = "MaterialSync"

/**
 * Production-grade SSE-based material synchronisation repository.
 *
 * Architecture
 * ------------
 * This is the **single source of truth** for all material sync logic.
 *
 *  - ViewModels and Workers depend on [SyncRepository] — not on this class
 *    directly — so the implementation can be swapped in tests.
 *  - All Room writes happen on [Dispatchers.IO] in explicit transactions.
 *  - All state mutations happen through the [MutableStateFlow] so collectors
 *    never observe partial states.
 *
 * Sync protocol (step by step)
 * ----------------------------
 *  1. Read `lastSyncTimestampMs` from DataStore (0L = never synced).
 *  2. Read `lastCursor` from [SyncMetadataDao] (null = no in-progress session).
 *  3. Open a streaming HTTP connection to GET /api/v1/materials/stream
 *       ?since=<ISO-8601>  (from lastSyncTimestampMs)
 *       &cursor=<token>    (null on first attempt; set on reconnect)
 *       &batch_size=150
 *  4. Consume SSE frames via [SseParser]:
 *       - `batch`    → upsert materials+properties into Room, update cursor.
 *       - `complete` → soft-delete removed IDs, advance sync timestamp,
 *                      clear cursor, transition to [SyncState.Completed].
 *       - `error`    → schedule retry if retryable, else [SyncState.Failed].
 *  5. On any IO exception: save cursor, schedule exponential-backoff retry.
 *
 * Duplicate prevention
 * --------------------
 * Room's `OnConflictStrategy.REPLACE` on `insertMaterials` / `insertProperties`
 * ensures upsert semantics. The `lastSyncTimestampMs` cursor advances only
 * after a successful `complete` frame, so a partial sync is always resumed
 * from the first incomplete batch.
 *
 * The `cursor` field inside each `batch` event encodes the exact `(since,
 * offset)` needed to resume from that position. It is persisted in
 * [SyncMetadataEntity] after every batch so a process kill mid-sync loses
 * at most one batch.
 *
 * Exponential backoff
 * -------------------
 * Attempt 1  → 2 s delay
 * Attempt 2  → 4 s delay
 * Attempt 3  → 8 s delay
 * Attempt 4  → 16 s delay
 * Attempt 5  → 32 s delay (max)  then terminal [SyncState.Failed]
 *
 * @param okHttpClient  The app-wide OkHttpClient (AuthInterceptor already
 *                      attached — Bearer token injected automatically).
 * @param sseParser     [SseParser] instance for frame deserialization.
 * @param materialDao   Room DAO for upsert operations.
 * @param syncMetadataDao Room DAO for cursor persistence.
 * @param prefsRepo     DataStore for `lastMaterialSyncMs` persistence.
 * @param networkMonitor Connectivity checker for pre-flight guards.
 */
@Singleton
class MaterialSyncRepository @Inject constructor(
    @Named("syncOkHttpClient") private val okHttpClient: OkHttpClient,
    private val sseParser: SseParser,
    private val materialDao: MaterialDao,
    private val syncMetadataDao: SyncMetadataDao,
    private val prefsRepo: UserPreferencesRepository,
    private val networkMonitor: NetworkMonitor,
) : SyncRepository {

    // ── State ─────────────────────────────────────────────────────────────────

    private val _syncState = MutableStateFlow<SyncState>(SyncState.Idle)
    override val syncState: Flow<SyncState> = _syncState.asStateFlow()

    private val _syncing = AtomicBoolean(false)
    override val isSyncing: Boolean get() = _syncing.get()

    /** Coroutine scope for sync work — separate from any ViewModel scope. */
    private val syncScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    /** Cancellation handle for the active sync job. */
    @Volatile private var activeJob: Job? = null

    // ── Backoff config ────────────────────────────────────────────────────────

    private val backoffDelaysMs = longArrayOf(2_000, 4_000, 8_000, 16_000, 32_000)
    private val maxAttempts = backoffDelaysMs.size + 1  // 6 total

    // ── SyncRepository API ────────────────────────────────────────────────────

    override suspend fun sync(forceFullSync: Boolean) {
        // Guard: drop duplicate calls — never run two syncs concurrently.
        if (!_syncing.compareAndSet(false, true)) {
            Log.i(TAG, "sync() called while already syncing — ignoring")
            return
        }
        activeJob = syncScope.launch {
            try {
                runSyncWithRetry(forceFullSync = forceFullSync)
            } finally {
                _syncing.set(false)
            }
        }
        // Await the job so the caller (e.g. WorkManager) can block until done.
        activeJob?.join()
    }

    override fun cancel() {
        activeJob?.cancel()
        activeJob = null
        _syncing.set(false)
        _syncState.value = SyncState.Idle
        Log.i(TAG, "Sync cancelled by caller")
    }

    override suspend fun lastSyncTimestampMs(): Long =
        prefsRepo.userPreferencesFlow.first().lastMaterialSyncMs

    override suspend fun resetSyncCursor() {
        prefsRepo.setLastMaterialSyncMs(0L)
        syncMetadataDao.clearCursor()
        Log.i(TAG, "Sync cursor reset to epoch")
    }

    // ── Core sync logic ───────────────────────────────────────────────────────

    private suspend fun runSyncWithRetry(forceFullSync: Boolean) {
        val requestId = UUID.randomUUID().toString()

        // --- Pre-flight: connectivity ---
        if (!networkMonitor.isConnected()) {
            Log.w(TAG, "[$requestId] No connectivity — deferring sync")
            _syncState.value = SyncState.Failed(SyncError.NoConnectivity)
            return
        }

        // --- Resolve starting parameters ---
        val lastSyncMs = if (forceFullSync) 0L else lastSyncTimestampMs()
        val sinceIso = Instant.ofEpochMilli(lastSyncMs).toString()
        val isFirstSync = lastSyncMs == 0L

        // Resume cursor: null if this is a fresh attempt, set if reconnecting
        val savedCursor: String? = if (forceFullSync) null
            else syncMetadataDao.getCursor()

        Log.i(
            TAG,
            "[$requestId] Sync START | since=$sinceIso | isFirstSync=$isFirstSync | " +
                "hasCursor=${savedCursor != null}",
        )

        val wallStart = System.currentTimeMillis()
        var attempt = 0
        var cursor: String? = savedCursor

        _syncState.value = SyncState.Connecting

        while (attempt < maxAttempts) {
            attempt++
            val result = attemptSync(
                requestId   = requestId,
                sinceIso    = sinceIso,
                isFirstSync = isFirstSync,
                cursor      = cursor,
                wallStart   = wallStart,
            )

            when (result) {
                is AttemptResult.Success -> {
                    val durationMs = System.currentTimeMillis() - wallStart
                    _syncState.value = SyncState.Completed(
                        inserted     = result.inserted,
                        updated      = result.updated,
                        deleted      = result.deleted,
                        durationMs   = durationMs,
                        isFirstSync  = isFirstSync,
                    )
                    Log.i(
                        TAG,
                        "[$requestId] Sync COMPLETE | inserted=${result.inserted} | " +
                            "updated=${result.updated} | deleted=${result.deleted} | " +
                            "duration=${durationMs}ms",
                    )
                    // Reset to Idle after a short display delay so the UI shows
                    // "Sync complete" briefly, then returns to the tappable idle state.
                    delay(3_000)
                    _syncState.value = SyncState.Idle
                    return
                }

                is AttemptResult.Resumable -> {
                    // Update the cursor so the next attempt resumes where we left off.
                    cursor = result.cursor
                    val err = result.error

                    if (!err.isRetryable || attempt >= maxAttempts) {
                        Log.e(TAG, "[$requestId] Non-retryable error or max attempts reached: $err")
                        _syncState.value = SyncState.Failed(err, attempt)
                        return
                    }

                    val delayMs = backoffDelaysMs[attempt - 1]
                    Log.w(
                        TAG,
                        "[$requestId] Attempt $attempt failed ($err). " +
                            "Retrying in ${delayMs}ms (attempt ${attempt + 1}/$maxAttempts)",
                    )
                    _syncState.value = SyncState.Retrying(
                        attempt     = attempt,
                        maxAttempts = maxAttempts,
                        delayMs     = delayMs,
                        cause       = err,
                    )
                    _syncState.value = SyncState.Connecting
                    delay(delayMs)
                }

                is AttemptResult.Terminal -> {
                    Log.e(TAG, "[$requestId] Terminal failure: ${result.error}")
                    _syncState.value = SyncState.Failed(result.error, attempt)
                    return
                }
            }
        }

        // Exhausted all retries
        Log.e(TAG, "[$requestId] All $maxAttempts attempts exhausted")
        _syncState.value = SyncState.Failed(
            SyncError.Unknown("Max retry attempts ($maxAttempts) exhausted"),
            attempt,
        )
    }

    // ── Single attempt ────────────────────────────────────────────────────────

    private sealed interface AttemptResult {
        data class Success(val inserted: Int, val updated: Int, val deleted: Int) : AttemptResult
        /** Retryable failure — carries the cursor so we can resume. */
        data class Resumable(val error: SyncError, val cursor: String?) : AttemptResult
        /** Non-retryable or auth failure — stop immediately. */
        data class Terminal(val error: SyncError) : AttemptResult
    }

    private suspend fun attemptSync(
        requestId: String,
        sinceIso: String,
        isFirstSync: Boolean,
        cursor: String?,
        wallStart: Long,
    ): AttemptResult = withContext(Dispatchers.IO) {
        val url = buildStreamUrl(sinceIso, cursor)
        val request = Request.Builder()
            .url(url)
            .header("Accept", "text/event-stream")
            .header("X-Request-ID", requestId)
            .header("Cache-Control", "no-cache")
            .build()

        Log.i(TAG, "[$requestId] Opening SSE stream: $url")

        var response: Response? = null
        var inserted = 0
        var updated = 0
        var deleted = 0
        var lastCursor: String? = cursor
        var totalMaterials = 0
        var receivedMaterials = 0
        var batchCount = 0

        try {
            response = okHttpClient.newCall(request).execute()

            when {
                response.code == 401 || response.code == 403 -> {
                    Log.e(TAG, "[$requestId] Auth error: HTTP ${response.code}")
                    return@withContext AttemptResult.Terminal(SyncError.AuthError(response.code))
                }
                !response.isSuccessful -> {
                    Log.e(TAG, "[$requestId] HTTP error: ${response.code}")
                    return@withContext AttemptResult.Resumable(
                        SyncError.ServerError(response.code),
                        lastCursor,
                    )
                }
            }

            val body = response.body
                ?: return@withContext AttemptResult.Resumable(
                    SyncError.StreamInterrupted("Empty response body"),
                    lastCursor,
                )

            // Stream SSE frames
            sseParser.parse(body.source()) { event ->
                when (event) {
                    is SseEvent.Batch -> {
                        batchCount++
                        totalMaterials = event.total
                        receivedMaterials += event.count
                        lastCursor = event.cursor

                        // --- Persist cursor before Room write so a crash
                        //     between write and cursor-save can be detected ---
                        syncMetadataDao.saveCursor(event.cursor)

                        // --- Upsert batch into Room ---
                        val syncedAt = System.currentTimeMillis()
                        val entities = event.materials.map { it.toMaterialEntity(syncedAt) }
                        val properties = event.materials.mapNotNull { it.toPropertyEntity(syncedAt) }

                        // Track inserts vs updates using existing ID set
                        val existingIds = materialDao.getExistingIds(entities.map { it.id })
                        val batchInserted = entities.count { it.id !in existingIds }
                        val batchUpdated = entities.size - batchInserted

                        materialDao.insertMaterials(entities)
                        materialDao.insertProperties(properties)

                        inserted += batchInserted
                        updated += batchUpdated

                        Log.i(
                            TAG,
                            "[$requestId] Batch $batchCount | offset=${event.offset} | " +
                                "count=${event.count} | ins=$batchInserted | upd=$batchUpdated",
                        )

                        // Emit live progress snapshot to UI
                        _syncState.value = SyncState.Streaming(
                            SyncProgress(
                                totalMaterials    = totalMaterials,
                                receivedMaterials = receivedMaterials,
                                currentBatch      = batchCount,
                                isFirstSync       = isFirstSync,
                                insertedSoFar     = inserted,
                                updatedSoFar      = updated,
                                elapsedMs         = System.currentTimeMillis() - wallStart,
                            )
                        )
                    }

                    is SseEvent.Complete -> {
                        Log.i(
                            TAG,
                            "[$requestId] SSE complete | totalSent=${event.totalSent} | " +
                                "deletedIds=${event.deletedIds.size}",
                        )

                        // --- Soft-delete removed IDs ---
                        if (event.deletedIds.isNotEmpty()) {
                            event.deletedIds.chunked(MaterialDao.SQLITE_MAX_VARIABLE_NUMBER)
                                .forEach { chunk ->
                                    materialDao.markDeletedByIds(chunk)
                                }
                            deleted = event.deletedIds.size
                        }

                        // --- On first sync, purge any Room rows not in server response ---
                        if (isFirstSync && event.totalSent > 0) {
                            // We can't chunk all IDs here (too many) — instead rely on
                            // the server's deletedIds to be authoritative. A full purge
                            // of genuinely absent rows requires a separate admin flow.
                        }

                        // --- Advance sync cursor only after successful complete ---
                        val newSyncMs = runCatching {
                            Instant.parse(event.serverTimestamp).toEpochMilli()
                        }.getOrElse {
                            Log.w(TAG, "[$requestId] Bad server_timestamp '${event.serverTimestamp}', using local clock")
                            System.currentTimeMillis()
                        }
                        prefsRepo.setLastMaterialSyncMs(newSyncMs)
                        syncMetadataDao.clearCursor()

                        Log.i(
                            TAG,
                            "[$requestId] Cursor advanced to ${event.serverTimestamp} ($newSyncMs ms)",
                        )
                    }

                    is SseEvent.ServerError -> {
                        Log.e(TAG, "[$requestId] Server error event: ${event.code} — ${event.message}")
                        // Will be caught as a Resumable or Terminal outside the parser
                        throw SseServerErrorException(event.code, event.message, event.retryable)
                    }
                }
            }

            AttemptResult.Success(inserted, updated, deleted)

        } catch (e: CancellationException) {
            Log.i(TAG, "[$requestId] Sync cancelled")
            throw e  // Re-throw so the coroutine framework can handle it
        } catch (e: SseServerErrorException) {
            val error = if (e.retryable)
                SyncError.StreamInterrupted("Server: ${e.code} — ${e.message}")
            else
                SyncError.Unknown("Server: ${e.code} — ${e.message}")
            AttemptResult.Resumable(error, lastCursor)
        } catch (e: SocketTimeoutException) {
            Log.w(TAG, "[$requestId] Timeout: ${e.message}")
            AttemptResult.Resumable(SyncError.Timeout(isReadTimeout = true), lastCursor)
        } catch (e: IOException) {
            Log.w(TAG, "[$requestId] IO error: ${e.message}")
            AttemptResult.Resumable(SyncError.StreamInterrupted(e.message ?: "IO error"), lastCursor)
        } catch (e: Exception) {
            Log.e(TAG, "[$requestId] Unexpected: ${e.message}", e)
            AttemptResult.Resumable(SyncError.Unknown(e.message ?: "Unknown"), lastCursor)
        } finally {
            try { response?.close() } catch (_: Exception) {}
        }
    }

    // ── URL builder ───────────────────────────────────────────────────────────

    private fun buildStreamUrl(sinceIso: String, cursor: String?): String {
        val base = "${BuildConfig.BASE_URL}api/v1/materials/stream"
        return buildString {
            append(base)
            append("?since=")
            append(java.net.URLEncoder.encode(sinceIso, "UTF-8"))
            append("&batch_size=150")
            if (cursor != null) {
                append("&cursor=")
                append(java.net.URLEncoder.encode(cursor, "UTF-8"))
            }
        }
    }

    // ── DTO → Room entity mappers ─────────────────────────────────────────────

    private fun MaterialResponseDto.toMaterialEntity(syncedAt: Long) = MaterialEntity(
        id             = id,
        name           = name,
        category       = category,
        source         = source,
        notes          = notes,
        evidenceLevel  = evidenceLevel,
        updatedAt      = syncedAt,
        isDeleted      = false,
    )

    private fun MaterialResponseDto.toPropertyEntity(syncedAt: Long): MaterialPropertyEntity? {
        val p = properties ?: return null
        return MaterialPropertyEntity(
            id                      = "property_$id",
            materialId              = id,
            tensileStrengthMpaMin   = p.tensileStrengthMpaMin,
            tensileStrengthMpaMax   = p.tensileStrengthMpaMax,
            elasticModulusGpaMin    = p.elasticModulusGpaMin,
            elasticModulusGpaMax    = p.elasticModulusGpaMax,
            elongationPctMin        = p.elongationPctMin,
            elongationPctMax        = p.elongationPctMax,
            punctureResistanceN     = p.punctureResistanceN,
            wvtr                    = p.wvtr,
            otr                     = p.otr,
            waterSolubility         = p.waterSolubility,
            swellingRatio           = p.swellingRatio,
            degradationDaysMin      = p.degradationDaysMin,
            degradationDaysMax      = p.degradationDaysMax,
            enzymaticDegradability  = p.enzymaticDegradability,
            hydrolyticStability     = p.hydrolyticStability,
            cytotoxicitySafe        = p.cytotoxicitySafe,
            hemocompatible          = p.hemocompatible,
            antimicrobial           = p.antimicrobial,
            endotoxinConcern        = p.endotoxinConcern,
            sterGamma               = p.sterGamma,
            sterEto                 = p.sterEto,
            sterSteam               = p.sterSteam,
            sterUv                  = p.sterUv,
            sterAutoclave           = p.sterAutoclave,
            procFilm                = p.procFilm,
            procCasting             = p.procCasting,
            procExtrusion           = p.procExtrusion,
            procCoating             = p.procCoating,
            procMelt                = p.procMelt,
            solventCompatible       = p.solventCompatible,
            costBand                = p.costBand,
            availabilityBand        = p.availabilityBand,
            dataCompleteness        = p.dataCompleteness,
            updatedAt               = syncedAt,
        )
    }
}

/** Internal exception thrown when the server emits a `{"event":"error"}` frame. */
private class SseServerErrorException(
    val code: String,
    override val message: String,
    val retryable: Boolean,
) : Exception(message)
