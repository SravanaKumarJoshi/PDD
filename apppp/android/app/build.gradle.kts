plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.google.dagger.hilt.android")
    id("org.jetbrains.kotlin.plugin.serialization")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.devtools.ksp")
    id("com.google.gms.google-services")
}

// Override when running on a USB-connected physical device, for example:
//   adb reverse tcp:8000 tcp:8000
//   .\gradlew.bat assembleDevDebug -PDEV_API_BASE_URL=http://127.0.0.1:8000/
// Without this property, dev builds keep the standard Android-emulator route.
val devApiBaseUrl = providers.gradleProperty("DEV_API_BASE_URL")
    .getOrElse("http://10.0.2.2:8000/")

android {
    namespace = "com.biopolymer.screening"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.biopolymer.screening"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        vectorDrawables {
            useSupportLibrary = true
        }

        // Room schema export
        // Room schema export (KSP)
        ksp {
            arg("room.schemaLocation", "$projectDir/schemas")
        }
    }

    // -------------------------------------------------------------------------
    // Build flavors — one per deployment environment.
    //
    // Each flavor injects a BASE_URL BuildConfig field that the networking
    // layer reads at runtime.  No hardcoded URLs appear anywhere in Kotlin code.
    //
    // Flavor       | Variant             | API target
    // ------------ | ------------------- | ---------------------------------
    // dev          | devDebug            | http://10.0.2.2:8000  (AVD only)
    //              |                     | http://192.168.x.x:8000 (real device)
    // staging      | stagingRelease      | https://api-staging.yourdomain.com
    // production   | productionRelease   | https://api.yourdomain.com
    //
    // To select a flavor in Android Studio: Build > Select Build Variant
    // To build from CLI:
    //   ./gradlew assembleDevDebug
    //   ./gradlew assembleStagingRelease
    //   ./gradlew assembleProductionRelease
    // -------------------------------------------------------------------------
    flavorDimensions += "environment"

    productFlavors {
        create("dev") {
            dimension = "environment"
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"

            // 10.0.2.2 is the AVD loopback to the host machine.  A physical
            // USB-connected device must use adb reverse plus
            // -PDEV_API_BASE_URL=http://127.0.0.1:8000/ instead.  This value
            // is ONLY present in debug builds; release builds of the dev
            // flavor should not be distributed.
            buildConfigField("String", "BASE_URL", "\"$devApiBaseUrl\"")

            // Allow plain HTTP in the dev flavor only (controlled via the
            // flavor-specific network security config).
            resValue("string", "app_name", "BioPolymer Dev")
        }

        create("staging") {
            dimension = "environment"
            applicationIdSuffix = ".staging"
            versionNameSuffix = "-staging"

            // Replace with your actual staging API domain before distributing.
            buildConfigField("String", "BASE_URL", "\"https://api-staging.yourdomain.com/\"")
            resValue("string", "app_name", "BioPolymer Staging")
        }

        create("production") {
            dimension = "environment"

            // Replace with your actual production API domain before releasing.
            buildConfigField("String", "BASE_URL", "\"https://api.yourdomain.com/\"")
            resValue("string", "app_name", "BioPolymer Screening")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
            // Ensure logging is stripped in release builds
            buildConfigField("Boolean", "ENABLE_HTTP_LOGGING", "false")
        }
        debug {
            isDebuggable = true
            buildConfigField("Boolean", "ENABLE_HTTP_LOGGING", "true")
        }
    }

    // -------------------------------------------------------------------------
    // Variant filter — block combinations that must never be built or
    // distributed.
    //
    // devRelease: The dev flavor uses http://10.0.2.2:8000/ (plain HTTP).
    //   A release-signed APK/AAB built from this flavor would contain an HTTP
    //   endpoint and cleartext-permitted network security config.  It must
    //   never be uploaded to the Play Store or distributed to users.
    //
    // stagingDebug / productionDebug: Debug builds of non-dev flavors are
    //   permitted for QA but should be blocked from automated release pipelines.
    //   Remove this block if your CI intentionally builds these variants.
    // -------------------------------------------------------------------------
    androidComponents {
        beforeVariants { variantBuilder ->
            if (variantBuilder.flavorName == "dev" && variantBuilder.buildType == "release") {
                // Prevent accidental release builds of the dev (HTTP) flavor.
                variantBuilder.enable = false
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        viewBinding = true
        // Required: exposes BuildConfig.BASE_URL and BuildConfig.ENABLE_HTTP_LOGGING
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    // Required: prevent .tflite from being compressed so it can be memory-mapped
    aaptOptions {
        noCompress += listOf("tflite")
    }
}

dependencies {
    // Firebase BOM
    implementation(platform("com.google.firebase:firebase-bom:33.10.0"))
    implementation("com.google.firebase:firebase-auth")
    implementation("com.google.firebase:firebase-analytics")

    // Google Sign-In
    implementation("com.google.android.gms:play-services-auth:21.2.0")

    // Core
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.6")
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.6")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.6")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.core:core-splashscreen:1.0.1")

    // Material Design
    implementation("com.google.android.material:material:1.12.0")

    // Compose BOM
    implementation(platform("androidx.compose:compose-bom:2024.09.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.8.0")

    // ConstraintLayout for XML
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")

    // Hilt
    implementation("com.google.dagger:hilt-android:2.51.1")
    ksp("com.google.dagger:hilt-compiler:2.51.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")
    implementation("androidx.hilt:hilt-work:1.2.0")
    ksp("androidx.hilt:hilt-compiler:1.2.0")

    // Room
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    ksp("androidx.room:room-compiler:2.6.1")
    testImplementation("androidx.room:room-testing:2.6.1")

    // Retrofit + Moshi
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.9.0")
    implementation("com.squareup.moshi:moshi-kotlin:1.15.0")
    ksp("com.squareup.moshi:moshi-kotlin-codegen:1.15.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // DataStore
    implementation("androidx.datastore:datastore-preferences:1.1.1")

    // WorkManager
    implementation("androidx.work:work-runtime-ktx:2.9.1")

    // Kotlinx Serialization
    implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.3")

    // Charts
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")

    // TensorFlow Lite — on-device polysaccharide classification
    implementation("org.tensorflow:tensorflow-lite:2.14.0")
    implementation("org.tensorflow:tensorflow-lite-support:0.4.4")

    // Testing
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.jetbrains.kotlinx:kotlinx-coroutines-test:1.8.1")
    testImplementation("io.mockk:mockk:1.13.12")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
    androidTestImplementation(platform("androidx.compose:compose-bom:2024.09.00"))
    androidTestImplementation("androidx.compose.ui:ui-test-junit4")
    debugImplementation("androidx.compose.ui:ui-tooling")
    debugImplementation("androidx.compose.ui:ui-test-manifest")
}
