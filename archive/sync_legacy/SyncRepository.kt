package com.biopolymer.screening.data.sync

import kotlinx.coroutines.flow.Flow

/**
 * Contract for the material synchronisation engine.
 *
 * Consumers (ViewModels, Workers) depend on this interface, not on the
 * concrete [MaterialSyncRepository], so they are trivially testable with
 * a fake/stub implementation and the real implementation can be swapped
 * without touching call sites.
 *
 * Sync lifecycle
 * --------------
 *
 *  1. Caller collects [syncState] to observe progress.
 *  2. Caller invokes [sync].
 *  3. The implementation emits [SyncState.Connecting], then successive
 *     [SyncState.Streaming] snapshots, then [SyncState.Completed] or
 *     [SyncState.Failed] / [SyncState.Retrying].
 *  4. After [SyncState.Completed] or a terminal [SyncState.Failed],
 *     the state returns to [SyncState.Idle].
 *
 * Thread safety
 * -------------
 * [sync] is a suspend function and must be called from a coroutine.
 * The backing StateFlow is thread-safe.  Multiple concurrent calls to
 * [sync] are serialised internally — a second call while a sync is in
 * progress is a no-op that returns immediately.
 */
interface SyncRepository {

    /**
     * Hot StateFlow of the current synchronisation state.
     *
     * Collect this in a ViewModel with `stateIn(viewModelScope)` so the UI
     * always sees the latest state even if it was emitted before collection
     * started.
     */
    val syncState: Flow<SyncState>

    /**
     * Run a full incremental sync.
     *
     * - On first run (no saved cursor): downloads the complete catalog in
     *   streamed batches, commits each batch to Room immediately.
     * - On subsequent runs: requests only rows whose `updated_at` is after
     *   the last successful sync timestamp.
     * - Retries automatically on transient failures using exponential backoff.
     * - Resumes mid-stream using the SSE cursor if the connection is dropped.
     *
     * This function is a no-op if a sync is already in progress.
     *
     * @param forceFullSync  When true, ignore the saved cursor and re-download
     *                       the complete catalog. Use only for admin/debug flows.
     */
    suspend fun sync(forceFullSync: Boolean = false)

    /**
     * Cancel any in-progress sync immediately.
     *
     * The sync state transitions to [SyncState.Idle]. Any partially written
     * Room data is retained so that a subsequent [sync] can resume from the
     * last successful cursor rather than starting over.
     */
    fun cancel()

    /**
     * Return true if a sync is currently in progress.
     *
     * Equivalent to checking `syncState.value is SyncState.Connecting ||
     * syncState.value is SyncState.Streaming`, but provided as a convenience
     * for WorkManager workers that cannot easily collect a Flow.
     */
    val isSyncing: Boolean

    /**
     * Epoch-milliseconds of the last *successful* sync, or 0L if the device
     * has never successfully synced.
     */
    suspend fun lastSyncTimestampMs(): Long

    /**
     * Reset the sync cursor to the Unix epoch.
     *
     * This forces the next [sync] call to re-download the complete catalog.
     * Use only from the "Delete All Local Data" settings action.
     */
    suspend fun resetSyncCursor()
}
