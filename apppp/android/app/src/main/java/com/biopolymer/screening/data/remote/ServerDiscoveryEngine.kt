package com.biopolymer.screening.data.remote

import android.content.Context
import android.net.wifi.WifiManager
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.InetAddress

private const val TAG = "ServerDiscovery"

/**
 * Engine that scans the local Wi-Fi subnet for active BioPolymer FastAPI servers on port 8000.
 */
class ServerDiscoveryEngine(
    private val context: Context,
) {
    private val client = OkHttpClient.Builder()
        .connectTimeout(500, java.util.concurrent.TimeUnit.MILLISECONDS)
        .readTimeout(500, java.util.concurrent.TimeUnit.MILLISECONDS)
        .writeTimeout(500, java.util.concurrent.TimeUnit.MILLISECONDS)
        .build()

    suspend fun discoverLocalServer(port: Int = 8000): String? = withContext(Dispatchers.IO) {
        val localIp = getLocalWifiIpAddress()
        if (localIp == null) {
            Log.w(TAG, "Cannot perform subnet scan — Wi-Fi IP address not available")
            return@withContext null
        }

        val prefix = localIp.substringBeforeLast(".")
        Log.i(TAG, "Starting local subnet scan on $prefix.1..254:$port...")

        // Quick check loopback/emulator first
        val defaultCandidates = listOf("10.0.2.2", "127.0.0.1", localIp)
        for (candidate in defaultCandidates) {
            val url = "http://$candidate:$port/"
            if (checkHealthAtUrl(url)) {
                Log.i(TAG, "Discovered active server at priority IP: $url")
                return@withContext url
            }
        }

        // Parallel scan subnet addresses 1..254
        val discoveredUrl = coroutineScope {
            (1..254).map { i ->
                val targetIp = "$prefix.$i"
                async {
                    val url = "http://$targetIp:$port/"
                    if (checkHealthAtUrl(url)) url else null
                }
            }.awaitAll().firstOrNull { it != null }
        }

        if (discoveredUrl != null) {
            Log.i(TAG, "Subnet scan successfully discovered BioPolymer server at: $discoveredUrl")
        } else {
            Log.w(TAG, "Subnet scan complete. No active BioPolymer server found on $prefix.0/24:$port")
        }

        discoveredUrl
    }

    private fun checkHealthAtUrl(baseUrl: String): Boolean {
        return try {
            val healthUrl = "${baseUrl.removeSuffix("/")}/health"
            val request = Request.Builder()
                .url(healthUrl)
                .get()
                .build()

            client.newCall(request).execute().use { response ->
                if (response.isSuccessful) {
                    val body = response.body?.string() ?: ""
                    body.contains("healthy") || body.contains("BioPolymer")
                } else {
                    false
                }
            }
        } catch (e: Exception) {
            false
        }
    }

    private fun getLocalWifiIpAddress(): String? {
        return try {
            val wifiManager = context.applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
            val ipInt = wifiManager?.connectionInfo?.ipAddress ?: 0
            if (ipInt == 0) {
                // Try network interfaces fallback
                val interfaces = java.net.NetworkInterface.getNetworkInterfaces()
                while (interfaces.hasMoreElements()) {
                    val iface = interfaces.nextElement()
                    val addresses = iface.inetAddresses
                    while (addresses.hasMoreElements()) {
                        val addr = addresses.nextElement()
                        if (!addr.isLoopbackAddress && addr is java.net.Inet4Address) {
                            return addr.hostAddress
                        }
                    }
                }
                null
            } else {
                String.format(
                    java.util.Locale.US,
                    "%d.%d.%d.%d",
                    ipInt and 0xff,
                    ipInt shr 8 and 0xff,
                    ipInt shr 16 and 0xff,
                    ipInt shr 24 and 0xff
                )
            }
        } catch (e: Exception) {
            Log.e(TAG, "Error resolving Wi-Fi IP: ${e.message}")
            null
        }
    }
}
