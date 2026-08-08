package com.biopolymer.screening.data.sync

import android.content.Context
import android.util.Log
import androidx.hilt.work.HiltWorker
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.OutOfQuotaPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first
import java.util.concurrent.TimeUnit

private const val TAG = "SyncWorker"

/**
 * WorkManager worker that runs the SSE material sync in the background.
 *
 * Two scheduling modes
 * --------------------
 * 1. **Periodic** — [enqueuePeriodicSync] schedules a recurring sync every
 *    [PERIODIC_SYNC_INTERVAL_HOURS] hours when the device has network access.
 *    WorkManager handles retries, doze mode, and process scheduling
 *    automatically.
 *
 * 2. **Immediate** — [enqueueImmediateSync] schedules a single expedited sync
 *    for user-initiated actions (e.g. the Settings "Sync Now" button) or when
 *    connectivity is first established after a period offline.
 *
 * Deduplication
 * -------------
 * Both modes use [WORK_NAME_PERIODIC] / [WORK_NAME_IMMEDIATE] as unique
 * work names so WorkManager never queues two syncs of the same type.
 * [ExistingPeriodicWorkPolicy.KEEP] means a running periodic sync is never
 * interrupted by a new schedule; [ExistingWorkPolicy.KEEP] for immediate
 * syncs means duplicate taps are silently dropped.
 *
 * Retry policy
 * ------------
 * The worker uses WorkManager's built-in exponential backoff starting at
 * [BACKOFF_DELAY_SECONDS] with an exponential multiplier.  This is in
 * addition to the application-level retries inside [MaterialSyncRepository],
 * which handle transient errors within a single WorkManager execution window.
 *
 * Idempotency
 * -----------
 * [MaterialSyncRepository.sync] is guarded by an [AtomicBoolean] so even if
 * the worker is invoked multiple times concurrently it will only run one sync.
 *
 * Result mapping
 * --------------
 * | SyncState outcome                       | WorkManager Result |
 * |-----------------------------------------|--------------------|
 * | SyncState.Completed                     | Success            |
 * | SyncState.Failed (retryable error)      | Retry              |
 * | SyncState.Failed (non-retryable error)  | Failure            |
 * | SyncState.Failed (auth error)           | Failure            |
 */
@HiltWorker
class MaterialSyncWorker @AssistedInject constructor(
    @Assisted context: Context,
    @Assisted params: WorkerParameters,
    private val syncRepository: SyncRepository,
) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        Log.i(TAG, "MaterialSyncWorker starting | attempt=${runAttemptCount + 1}")

        // Run the full incremental sync (or first-time full download).
        syncRepository.sync(forceFullSync = false)

        // Observe the final state to map to a WorkManager Result.
        return when (val state = syncRepository.syncState.first { it !is SyncState.Connecting && it !is SyncState.Streaming }) {
            is SyncState.Completed -> {
                Log.i(
                    TAG,
                    "Sync completed | inserted=${state.inserted} updated=${state.updated} " +
                        "deleted=${state.deleted} durationMs=${state.durationMs}",
                )
                Result.success()
            }

            is SyncState.Failed -> {
                val retryable = state.error.isRetryable &&
                    state.error !is SyncError.AuthError &&
                    state.error !is SyncError.LowStorage

                if (retryable) {
                    Log.w(TAG, "Sync failed (retryable): ${state.error} — scheduling WorkManager retry")
                    Result.retry()
                } else {
                    Log.e(TAG, "Sync failed (terminal): ${state.error} — no WorkManager retry")
                    Result.failure()
                }
            }

            // Should not happen — sync() always settles into Completed or Failed —
            // but treat any other terminal-ish state as retryable.
            else -> {
                Log.w(TAG, "Unexpected final state: $state — retrying")
                Result.retry()
            }
        }
    }

    companion object {

        /** Unique tag for periodic background sync work. */
        const val WORK_NAME_PERIODIC = "material_sync_periodic"

        /** Unique tag for user-triggered / connectivity-restored immediate sync. */
        const val WORK_NAME_IMMEDIATE = "material_sync_immediate"

        /** How often the periodic sync fires when conditions are met. */
        const val PERIODIC_SYNC_INTERVAL_HOURS = 6L

        /** Initial WorkManager backoff before the first retry. */
        const val BACKOFF_DELAY_SECONDS = 30L

        /** Shared constraints: require any working network connection. */
        private val networkConstraints = Constraints.Builder()
            .setRequiredNetworkType(NetworkType.CONNECTED)
            .build()

        /**
         * Schedule or update the periodic background sync.
         *
         * Call this once from [BiopolymerApp.onCreate] and from
         * [ConnectivitySyncScheduler] when connectivity is restored.
         *
         * [ExistingPeriodicWorkPolicy.KEEP] — if a periodic sync is already
         * scheduled, leave it untouched.  Use [ExistingPeriodicWorkPolicy.UPDATE]
         * only when the interval or constraints change.
         */
        fun enqueuePeriodicSync(workManager: WorkManager) {
            val request = PeriodicWorkRequestBuilder<MaterialSyncWorker>(
                repeatInterval = PERIODIC_SYNC_INTERVAL_HOURS,
                repeatIntervalTimeUnit = TimeUnit.HOURS,
                flexTimeInterval = 30,
                flexTimeIntervalUnit = TimeUnit.MINUTES,
            )
                .setConstraints(networkConstraints)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    BACKOFF_DELAY_SECONDS,
                    TimeUnit.SECONDS,
                )
                .addTag(WORK_NAME_PERIODIC)
                .build()

            workManager.enqueueUniquePeriodicWork(
                WORK_NAME_PERIODIC,
                ExistingPeriodicWorkPolicy.KEEP,
                request,
            )
            Log.i(TAG, "Periodic sync enqueued (every ${PERIODIC_SYNC_INTERVAL_HOURS}h)")
        }

        /**
         * Enqueue a one-shot expedited sync.
         *
         * Expedited work runs as soon as possible regardless of doze mode.
         * Use this for:
         *  - User-initiated "Sync Now" taps in Settings
         *  - Connectivity-restored triggers
         *  - Post-login first-sync
         *
         * [ExistingWorkPolicy.KEEP] prevents duplicate queuing when the user
         * taps "Sync Now" repeatedly.
         */
        fun enqueueImmediateSync(workManager: WorkManager) {
            val request = OneTimeWorkRequestBuilder<MaterialSyncWorker>()
                .setConstraints(networkConstraints)
                .setExpedited(OutOfQuotaPolicy.RUN_AS_NON_EXPEDITED_WORK_REQUEST)
                .setBackoffCriteria(
                    BackoffPolicy.EXPONENTIAL,
                    BACKOFF_DELAY_SECONDS,
                    TimeUnit.SECONDS,
                )
                .addTag(WORK_NAME_IMMEDIATE)
                .build()

            workManager.enqueueUniqueWork(
                WORK_NAME_IMMEDIATE,
                ExistingWorkPolicy.KEEP,
                request,
            )
            Log.i(TAG, "Immediate sync enqueued")
        }
    }
}
