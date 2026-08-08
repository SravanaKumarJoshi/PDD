package com.biopolymer.screening.data.remote

import com.biopolymer.screening.data.local.UserPreferences
import com.biopolymer.screening.data.local.UserPreferencesRepository
import io.mockk.every
import io.mockk.mockk
import kotlinx.coroutines.flow.flowOf
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test

class BaseUrlProviderTest {

    private lateinit var userPreferencesRepository: UserPreferencesRepository
    private lateinit var baseUrlProvider: BaseUrlProvider

    @Before
    fun setUp() {
        userPreferencesRepository = mockk(relaxed = true)
        every { userPreferencesRepository.userPreferencesFlow } returns flowOf(UserPreferences())
        baseUrlProvider = BaseUrlProvider(userPreferencesRepository)
    }

    @Test
    fun isEmulator_returnsTrueForEmulatorBuildInfo() {
        val emuInfo = DeviceBuildInfo(
            fingerprint = "google/sdk_gphone64_x86_64/sdk_gphone64_x86_64:12/SE1A.220826.008/8941916:userdebug/dev-keys",
            model = "sdk_gphone64_x86_64",
            manufacturer = "Google",
            hardware = "ranchu",
            brand = "google",
            device = "emulator64_x86_64",
            product = "sdk_gphone64_x86_64"
        )
        assertTrue(BaseUrlProvider.isEmulator(emuInfo))
    }

    @Test
    fun isEmulator_returnsFalseForPhysicalDeviceBuildInfo() {
        val physicalInfo = DeviceBuildInfo(
            fingerprint = "samsung/a52sxqx/a52s:13/TP1A.220624.014/A528BXXS5EWG1:user/release-keys",
            model = "SM-A528B",
            manufacturer = "samsung",
            hardware = "qcom",
            brand = "samsung",
            device = "a52sxq",
            product = "a52sxqx"
        )
        assertFalse(BaseUrlProvider.isEmulator(physicalInfo))
    }

    @Test
    fun resolveEffectiveUrl_onEmulator_usesEmulatorAddress() {
        val emuInfo = DeviceBuildInfo(
            fingerprint = "generic/sdk/generic:10/OSR1.180418.003/123456:userdebug/test-keys",
            model = "Android SDK built for x86",
            hardware = "goldfish"
        )
        val resolved = baseUrlProvider.resolveEffectiveUrl(
            customUrl = null,
            lastSuccessfulUrl = null,
            buildInfo = emuInfo
        )
        assertTrue("Emulator must use 10.0.2.2", resolved.contains("10.0.2.2"))
    }

    @Test
    fun resolveEffectiveUrl_onPhysicalDevice_neverReturns10_0_2_2() {
        val physicalInfo = DeviceBuildInfo(
            fingerprint = "google/Pixel 6/Pixel 6:13/TP1A.220624.014/123456:user/release-keys",
            model = "Pixel 6",
            manufacturer = "Google",
            hardware = "oriole"
        )
        val resolved = baseUrlProvider.resolveEffectiveUrl(
            customUrl = null,
            lastSuccessfulUrl = null,
            buildInfo = physicalInfo
        )
        assertFalse("Physical device must NEVER return 10.0.2.2", resolved.contains("10.0.2.2"))
        assertEquals("http://127.0.0.1:8000/", resolved)
    }

    @Test
    fun resolveEffectiveUrl_onPhysicalDevice_usesLastSuccessfulUrlIfAvailable() {
        val physicalInfo = DeviceBuildInfo(
            fingerprint = "samsung/galaxy/galaxy:12/123456:user/release-keys",
            model = "SM-G998B",
            manufacturer = "samsung"
        )
        val resolved = baseUrlProvider.resolveEffectiveUrl(
            customUrl = null,
            lastSuccessfulUrl = "http://192.168.1.42:8000/",
            buildInfo = physicalInfo
        )
        assertEquals("http://192.168.1.42:8000/", resolved)
    }

    @Test
    fun resolveEffectiveUrl_onPhysicalDevice_usesSavedCustomUrl() {
        val physicalInfo = DeviceBuildInfo(
            model = "Pixel 7 Pro",
            manufacturer = "Google"
        )
        val resolved = baseUrlProvider.resolveEffectiveUrl(
            customUrl = "http://10.200.49.220:8000/",
            lastSuccessfulUrl = null,
            buildInfo = physicalInfo
        )
        assertEquals("http://10.200.49.220:8000/", resolved)
    }
}
