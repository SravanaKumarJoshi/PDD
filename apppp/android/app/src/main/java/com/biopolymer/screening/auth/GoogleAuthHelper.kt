package com.biopolymer.screening.auth

import android.content.Context
import android.content.Intent
import android.util.Log
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInClient
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import com.google.android.gms.common.api.CommonStatusCodes
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.GoogleAuthProvider

/**
 * Shared utility for Google Sign-In authentication using Firebase Auth.
 *
 * Encapsulates the GoogleSignInClient configuration, intent creation,
 * and Firebase credential exchange. Used by both LoginActivity and SignUpActivity
 * to avoid duplicating authentication logic.
 *
 * Usage:
 * 1. Create an instance: `GoogleAuthHelper(context, webClientId)`
 * 2. Launch sign-in: `launcher.launch(helper.getSignInIntent())`
 * 3. Handle result: `helper.handleSignInResult(data, auth) { success, user, error -> ... }`
 */
class GoogleAuthHelper(context: Context, webClientId: String) {

    companion object {
        private const val TAG = "GoogleAuthHelper"
    }

    private val googleSignInClient: GoogleSignInClient

    init {
        val gso = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestIdToken(webClientId)
            .requestEmail()
            .requestProfile()
            .build()

        googleSignInClient = GoogleSignIn.getClient(context, gso)
    }

    /**
     * Returns the Intent to launch the Google account picker.
     * Pass this to an ActivityResultLauncher.
     */
    fun getSignInIntent(): Intent = googleSignInClient.signInIntent

    /**
     * Signs out the current Google account.
     * Call this when the user explicitly signs out of the app.
     */
    fun signOut(onComplete: () -> Unit = {}) {
        googleSignInClient.signOut().addOnCompleteListener { onComplete() }
    }

    /**
     * Handles the result from the Google Sign-In activity.
     *
     * Extracts the ID token from the result, exchanges it for a Firebase credential,
     * and calls the callback with the result.
     *
     * @param data The Intent data from the ActivityResult.
     * @param auth The FirebaseAuth instance.
     * @param callback Called with (success, user, errorMessage).
     */
    fun handleSignInResult(
        data: Intent?,
        auth: FirebaseAuth,
        callback: (success: Boolean, user: FirebaseUser?, errorMessage: String?) -> Unit
    ) {
        try {
            val task = GoogleSignIn.getSignedInAccountFromIntent(data)
            val account = task.getResult(ApiException::class.java)

            val idToken = account?.idToken
            if (idToken == null) {
                Log.e(TAG, "Google Sign-In succeeded but ID token is null")
                callback(false, null, "Authentication failed: no credentials received.")
                return
            }

            firebaseAuthWithGoogle(idToken, auth, callback)

        } catch (e: ApiException) {
            val errorMessage = mapApiExceptionToMessage(e)
            Log.w(TAG, "Google Sign-In failed: status code=${e.statusCode}", e)
            callback(false, null, errorMessage)
        }
    }

    /**
     * Exchanges a Google ID token for a Firebase credential and signs in.
     */
    private fun firebaseAuthWithGoogle(
        idToken: String,
        auth: FirebaseAuth,
        callback: (success: Boolean, user: FirebaseUser?, errorMessage: String?) -> Unit
    ) {
        val credential = GoogleAuthProvider.getCredential(idToken, null)
        auth.signInWithCredential(credential)
            .addOnSuccessListener { result ->
                Log.d(TAG, "Firebase auth with Google succeeded: ${result.user?.email}")
                callback(true, result.user, null)
            }
            .addOnFailureListener { exception ->
                Log.e(TAG, "Firebase auth with Google failed", exception)
                callback(
                    false,
                    null,
                    exception.localizedMessage ?: "Authentication failed. Please try again."
                )
            }
    }

    /**
     * Maps Google API exceptions to user-friendly error messages.
     */
    private fun mapApiExceptionToMessage(exception: ApiException): String {
        return when (exception.statusCode) {
            CommonStatusCodes.CANCELED,
            CommonStatusCodes.SIGN_IN_REQUIRED -> "Sign-in cancelled."

            CommonStatusCodes.NETWORK_ERROR -> "Network error. Please check your connection."

            CommonStatusCodes.DEVELOPER_ERROR ->
                "Configuration error. Please contact support. (DEVELOPER_ERROR)"

            CommonStatusCodes.INTERNAL_ERROR -> "An internal error occurred. Please try again."

            else -> "Sign-in failed (error ${exception.statusCode}). Please try again."
        }
    }
}
