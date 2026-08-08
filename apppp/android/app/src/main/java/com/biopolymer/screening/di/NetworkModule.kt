package com.biopolymer.screening.di

import android.content.Context
import android.util.Log
import com.biopolymer.screening.BuildConfig
import com.biopolymer.screening.data.remote.ApiService
import com.biopolymer.screening.data.remote.AuthInterceptor
import com.biopolymer.screening.data.remote.BaseUrlProvider
import com.biopolymer.screening.data.remote.DynamicBaseUrlInterceptor
import com.biopolymer.screening.data.remote.RetryInterceptor
import com.biopolymer.screening.data.remote.ServerDiscoveryEngine
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import okhttp3.CipherSuite
import okhttp3.Call
import okhttp3.ConnectionSpec
import okhttp3.EventListener
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Protocol
import okhttp3.Response
import okhttp3.TlsVersion
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.io.IOException
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Proxy
import java.util.UUID
import java.util.concurrent.TimeUnit
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object NetworkModule {

    private class RequestLifecycleEventListener : EventListener() {
        private val startNs = System.nanoTime()

        private fun id(call: Call) = call.request().header("X-Request-ID") ?: "?"
        private fun elapsedMs() = (System.nanoTime() - startNs) / 1_000_000L

        override fun dnsStart(call: Call, domainName: String) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] DNS start host=$domainName")
        }

        override fun dnsEnd(call: Call, domainName: String, inetAddressList: List<InetAddress>) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] DNS end host=$domainName addresses=$inetAddressList elapsed=${elapsedMs()}ms")
        }

        override fun connectStart(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] connect start address=$inetSocketAddress elapsed=${elapsedMs()}ms")
        }

        override fun connectEnd(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy, protocol: Protocol?) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] connect end protocol=$protocol elapsed=${elapsedMs()}ms")
        }

        override fun connectFailed(call: Call, inetSocketAddress: InetSocketAddress, proxy: Proxy, protocol: Protocol?, ioe: IOException) {
            Log.e("OkHttp-Lifecycle", "[${id(call)}] connect failed address=$inetSocketAddress elapsed=${elapsedMs()}ms: ${ioe::class.java.simpleName}: ${ioe.message}", ioe)
        }

        override fun requestHeadersEnd(call: Call, request: okhttp3.Request) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] request sent ${request.method} ${request.url.encodedPath} elapsed=${elapsedMs()}ms")
        }

        override fun responseHeadersEnd(call: Call, response: Response) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] response headers status=${response.code} elapsed=${elapsedMs()}ms")
        }

        override fun responseBodyEnd(call: Call, byteCount: Long) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] response body bytes=$byteCount elapsed=${elapsedMs()}ms")
        }

        override fun callEnd(call: Call) {
            Log.d("OkHttp-Lifecycle", "[${id(call)}] call complete elapsed=${elapsedMs()}ms")
        }

        override fun callFailed(call: Call, ioe: IOException) {
            Log.e("OkHttp-Lifecycle", "[${id(call)}] call failed elapsed=${elapsedMs()}ms: ${ioe::class.java.simpleName}: ${ioe.message}", ioe)
        }
    }

    @Provides
    @Singleton
    fun provideMoshi(): Moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()

    private object RequestIdInterceptor : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val original = chain.request()
            val req = if (original.header("X-Request-ID") == null) {
                original.newBuilder()
                    .header("X-Request-ID", UUID.randomUUID().toString())
                    .build()
            } else {
                original
            }
            return chain.proceed(req)
        }
    }

    private object TimingInterceptor : Interceptor {
        private const val TAG = "OkHttp-Timing"
        private const val SLOW_CALL_THRESHOLD_MS = 5_000L

        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request()
            val requestId = request.header("X-Request-ID") ?: "?"
            val method = request.method
            val url = request.url

            Log.d(TAG, "→ [$requestId]  $method  $url")

            val startNs = System.nanoTime()
            val response: Response = try {
                chain.proceed(request)
            } catch (error: IOException) {
                val elapsedMs = (System.nanoTime() - startNs) / 1_000_000L
                Log.e(TAG, "✖ [$requestId] $method ${url.encodedPath} failed after ${elapsedMs}ms: ${error::class.java.simpleName}: ${error.message}", error)
                throw error
            }
            val elapsedMs = (System.nanoTime() - startNs) / 1_000_000L

            val path = url.encodedPath
            val status = response.code
            val serverTiming = response.header("X-Response-Time-Ms")
            val serverNote = if (serverTiming != null) "  server=${serverTiming}ms" else ""

            val isSlow = elapsedMs > SLOW_CALL_THRESHOLD_MS
            val prefix = if (isSlow) "⚠ SLOW [$requestId]" else "← [$requestId]"
            val logLine = "$prefix  $method  $path  $status  ${elapsedMs}ms$serverNote"

            Log.d(TAG, logLine)
            if (isSlow) Log.w(TAG, logLine)

            return response
        }
    }

    @Provides
    @Singleton
    fun provideOkHttpClient(
        authInterceptor: AuthInterceptor,
        dynamicBaseUrlInterceptor: DynamicBaseUrlInterceptor,
        retryInterceptor: RetryInterceptor,
    ): OkHttpClient {
        val builder = OkHttpClient.Builder()
            // 1. Dynamic URL rewriting — update host/port/scheme on the fly from BaseUrlProvider
            .addInterceptor(dynamicBaseUrlInterceptor)

            // 2. Correlation ID
            .addInterceptor(RequestIdInterceptor)

            // 3. Auth Bearer Token
            .addInterceptor(authInterceptor)

            // 4. Exponential Backoff Retries for transient connection errors
            .addInterceptor(retryInterceptor)

            // 5. Timing measurement
            .addInterceptor(TimingInterceptor)

            // 6. Body logging (debug builds)
            .apply {
                if (BuildConfig.ENABLE_HTTP_LOGGING) {
                    addInterceptor(
                        HttpLoggingInterceptor().apply {
                            level = HttpLoggingInterceptor.Level.BODY
                        },
                    )
                }
            }

            // Timeouts
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .callTimeout(60, TimeUnit.SECONDS)

            .retryOnConnectionFailure(true)
            .eventListenerFactory(EventListener.Factory { RequestLifecycleEventListener() })
            .apply {
                if (!BuildConfig.DEBUG) {
                    connectionSpecs(
                        listOf(
                            ConnectionSpec.Builder(ConnectionSpec.MODERN_TLS)
                                .tlsVersions(TlsVersion.TLS_1_3, TlsVersion.TLS_1_2)
                                .cipherSuites(
                                    CipherSuite.TLS_AES_128_GCM_SHA256,
                                    CipherSuite.TLS_AES_256_GCM_SHA384,
                                    CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
                                    CipherSuite.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
                                    CipherSuite.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
                                    CipherSuite.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
                                    CipherSuite.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
                                    CipherSuite.TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256,
                                    CipherSuite.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256,
                                )
                                .build(),
                        ),
                    )
                }
            }

        return builder.build()
    }

    @Provides
    @Singleton
    fun provideRetrofit(
        client: OkHttpClient,
        moshi: Moshi,
        baseUrlProvider: BaseUrlProvider,
    ): Retrofit {
        val initialUrl = baseUrlProvider.getBaseUrl()
        Log.i("NetworkModule", "Initializing Retrofit with base URL: $initialUrl")
        return Retrofit.Builder()
            .baseUrl(initialUrl)
            .client(client)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()
    }

    @Provides
    @Singleton
    fun provideApiService(retrofit: Retrofit): ApiService =
        retrofit.create(ApiService::class.java)

    @Provides
    @Singleton
    fun provideServerDiscoveryEngine(
        @ApplicationContext context: Context
    ): ServerDiscoveryEngine = ServerDiscoveryEngine(context)
}

