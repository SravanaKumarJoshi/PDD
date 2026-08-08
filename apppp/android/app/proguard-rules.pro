# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in the SDK tools.

# Keep Moshi adapters
-keep class com.biopolymer.screening.data.remote.** { *; }
-keepclassmembers class * {
    @com.squareup.moshi.Json <fields>;
}

# Keep Room entities
-keep class com.biopolymer.screening.data.local.entity.** { *; }

# Keep Hilt generated classes
-keep class dagger.hilt.** { *; }
-keep class javax.inject.** { *; }
-keep @dagger.hilt.android.lifecycle.HiltViewModel class * { *; }

# Firebase
-keep class com.google.firebase.** { *; }
