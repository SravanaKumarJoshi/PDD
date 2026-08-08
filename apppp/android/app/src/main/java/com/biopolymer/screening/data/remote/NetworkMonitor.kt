package com.biopolymer.screening.data.remote

import android.content.Context
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.flow.conflate
import kotlinx.coroutines.flow.distinctUntilChanged
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Observes device network connectivity as a [Flow].
 *
 * Emits [NetworkStatus.Available] when at least one network with internet
 * capability is connected, and [NetworkStatus.Unavailable] when connectivity
 * is lost.
 *
 * Usage in a ViewModel:
 * ```kotlin
 * networkMonitor.status
 *     .onEach { status ->
 *         _isOffline.value = status == NetworkStatus.Unavailable
 *     }
 *     .launchIn(viewModelScope)
 * ```
 *
 * [conflate] ensures that rapid back-and-forth changes (e.g. flaky Wi-Fi)
 * don't flood the collector — only the most recent value is delivered if the
 * collector is slow.
 *
 * [distinctUntilChanged] prevents duplicate emissions when the same status is
 * reported consecutively (e.g. multiple AVAILABLE callbacks for the same
 * network).
 */
@Singleton
class NetworkMonitor @Inject constructor(
    @ApplicationContext private val context: Context,
) {

    sealed interface NetworkStatus {
        /** At least one network with internet capability is connected. */
        data object Available : NetworkStatus

        /** No network with internet capability is available. */
        data object Unavailable : NetworkStatus
    }

    val status: Flow<NetworkStatus> = callbackFlow {
        val connectivityManager =
            context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager

        val callback = object : ConnectivityManager.NetworkCallback() {
            override fun onAvailable(network: Network) {
                trySend(NetworkStatus.Available)
            }

            override fun onLost(network: Network) {
                // Check whether any OTHER network is still available before
                // reporting unavailability.
                val hasNetwork = connectivityManager
                    .getNetworkCapabilities(connectivityManager.activeNetwork)
                    ?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true

                if (!hasNetwork) {
                    trySend(NetworkStatus.Unavailable)
                }
            }

            override fun onUnavailable() {
                trySend(NetworkStatus.Unavailable)
            }
        }

        val request = NetworkRequest.Builder()
            .addCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
            .addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
            .addTransportType(NetworkCapabilities.TRANSPORT_ETHERNET)
            .build()

        // Emit the current state immediately so collectors don't have to wait
        // for the next connectivity change.
        val currentStatus = currentNetworkStatus(connectivityManager)
        trySend(currentStatus)

        connectivityManager.registerNetworkCallback(request, callback)

        awaitClose {
            connectivityManager.unregisterNetworkCallback(callback)
        }
    }
        .distinctUntilChanged()
        .conflate()

    /**
     * Returns the current network status synchronously.
     * Safe to call from any thread.
     */
    fun isConnected(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        return cm.getNetworkCapabilities(cm.activeNetwork)
            ?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true
    }

    private fun currentNetworkStatus(
        connectivityManager: ConnectivityManager,
    ): NetworkStatus {
        val capabilities =
            connectivityManager.getNetworkCapabilities(connectivityManager.activeNetwork)
        return if (capabilities?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET) == true) {
            NetworkStatus.Available
        } else {
            NetworkStatus.Unavailable
        }
    }
}
