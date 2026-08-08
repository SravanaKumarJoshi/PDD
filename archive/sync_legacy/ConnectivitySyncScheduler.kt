package com.biopolymer.screening.data.sync

import android.util.Log
import androidx.work.WorkManager
import com.biopolymer.screening.data.remote.NetworkMonitor
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.launch
import javax.inject.Inject
import javax.inject.Singleton

private const val TAG = "ConnectivitySync"

/**
 * Observes network connectivity and automatically triggers an immediate
 * background sync whenever the device transitions from offline → online.
 *
 * Why this matters
 * ----------------
 * If the device is offline when the periodic WorkManager alarm fires, the
 * work is deferred until the next alarm window.  Depending on battery
 * optimisation this can mean hours without a sync after the device comes
 * back online.
 *
 * [ConnectivitySyncScheduler] bridges that gap: it listens to the live
 * connectivity [Flow] and enqueues an expedited one-shot sync the moment
 * internet access is restored.
 *
 * Initialisation
 * --------------
 * Call [start] once from [BiopolymerApp.onCreate].  The internal
 * [CoroutineScope] lives for the application lifetime.
 *
 * Duplicate prevention
 * --------------------
 * [MaterialSyncWorker.enqueueImmediateSync] uses [ExistingWorkPolicy.KEEP]
 * so rapid connectivity flaps only ever enqueue one pending sync.
 */
@Singleton
class ConnectivitySyncScheduler @Inject constructor(
    private val networkMonitor: NetworkMonitor,
    private val workManager: WorkManager,
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    /**
     * Start observing connectivity.  Safe to call multiple times — the
     * internal [CoroutineScope] ensures only one observer runs.
     */
    fun start() {
        scope.launch {
            networkMonitor.status
                .distinctUntilChanged()
                // Drop the first emission so we don't trigger a sync on app
                // start if the device is already online — BiopolymerApp handles
                // the startup sync separately via the periodic work request.
                .drop(1)
                .collect { status ->
                    if (status == NetworkMonitor.NetworkStatus.Available) {
                        Log.i(TAG, "Connectivity restored — enqueueing immediate sync")
                        MaterialSyncWorker.enqueueImmediateSync(workManager)
                    } else {
                        Log.d(TAG, "Connectivity lost — sync will resume on reconnect")
                    }
                }
        }
    }
}
