package com.biopolymer.screening

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.util.Patterns
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.biopolymer.screening.databinding.ActivityLoginBinding
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser

class LoginActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "LoginActivity"
    }

    private lateinit var binding: ActivityLoginBinding
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        WindowCompat.setDecorFitsSystemWindows(window, false)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        auth = FirebaseAuth.getInstance()

        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        setupClickListeners()
    }

    private fun setupClickListeners() {
        binding.btnLogin.setOnClickListener {
            validateAndLogin()
        }

        binding.tvSignupLink.setOnClickListener {
            startActivity(Intent(this, SignUpActivity::class.java))
        }

        binding.tvForgotPassword.setOnClickListener {
            Toast.makeText(this, "Feature coming soon", Toast.LENGTH_SHORT).show()
        }
    }

    // ──────────────────────────────────────────────
    // Email/Password Login
    // ──────────────────────────────────────────────

    private fun validateAndLogin() {
        val email = binding.etEmail.text.toString().trim()
        val password = binding.etPassword.text.toString().trim()

        var isValid = true

        if (email.isEmpty() || !Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            binding.tilEmail.error = "Please enter a valid email"
            isValid = false
        } else {
            binding.tilEmail.error = null
        }

        if (password.length < 6) {
            binding.tilPassword.error = "Password must be at least 6 characters"
            isValid = false
        } else {
            binding.tilPassword.error = null
        }

        if (isValid) {
            performLogin(email, password)
        }
    }

    private fun performLogin(email: String, password: String) {
        binding.progressBar.visibility = View.VISIBLE
        binding.btnLogin.visibility = View.INVISIBLE

        auth.signInWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                binding.progressBar.visibility = View.GONE
                binding.btnLogin.visibility = View.VISIBLE

                if (task.isSuccessful) {
                    saveSessionAndNavigate(auth.currentUser)
                } else {
                    val errorMsg = mapFirebaseAuthError(task.exception)
                    binding.tilEmail.error = null
                    binding.tilPassword.error = null

                    when {
                        errorMsg.type == AuthErrorType.WRONG_PASSWORD ->
                            binding.tilPassword.error = errorMsg.message
                        errorMsg.type == AuthErrorType.WRONG_EMAIL ->
                            binding.tilEmail.error = errorMsg.message
                        else ->
                            Toast.makeText(this, errorMsg.message, Toast.LENGTH_LONG).show()
                    }
                }
            }
    }

    // ──────────────────────────────────────────────
    // Firebase Auth Error Mapping
    // ──────────────────────────────────────────────

    /** Categories of sign-in failure used to route inline vs. toast errors. */
    private enum class AuthErrorType {
        WRONG_PASSWORD, WRONG_EMAIL, TOO_MANY_ATTEMPTS, NETWORK, GENERIC
    }

    private data class AuthError(val type: AuthErrorType, val message: String)

    /**
     * Maps a Firebase AuthException to a typed, user-friendly [AuthError].
     * The error code is extracted from the exception message because the
     * FirebaseAuthException class is not always available at runtime.
     */
    private fun mapFirebaseAuthError(exception: Exception?): AuthError {
        val code = exception?.message ?: ""
        return when {
            // Wrong password for a valid account
            code.contains("INVALID_PASSWORD", ignoreCase = true) ||
            code.contains("wrong-password", ignoreCase = true) ->
                AuthError(AuthErrorType.WRONG_PASSWORD,
                    "Incorrect password. Please try again or use 'Forgot Password'.")

            // Email address not registered
            code.contains("USER_NOT_FOUND", ignoreCase = true) ||
            code.contains("no user record", ignoreCase = true) ||
            code.contains("user-not-found", ignoreCase = true) ->
                AuthError(AuthErrorType.WRONG_EMAIL,
                    "No account found with this email address.")

            // Email format invalid (should be caught locally, but guard here too)
            code.contains("INVALID_EMAIL", ignoreCase = true) ||
            code.contains("invalid-email", ignoreCase = true) ->
                AuthError(AuthErrorType.WRONG_EMAIL,
                    "The email address is badly formatted.")

            // Account disabled by admin
            code.contains("USER_DISABLED", ignoreCase = true) ||
            code.contains("user-disabled", ignoreCase = true) ->
                AuthError(AuthErrorType.GENERIC,
                    "This account has been disabled. Please contact support.")

            // Too many failed attempts
            code.contains("TOO_MANY_ATTEMPTS_TRY_LATER", ignoreCase = true) ||
            code.contains("too-many-requests", ignoreCase = true) ||
            code.contains("TOO_MANY_REQUESTS", ignoreCase = true) ->
                AuthError(AuthErrorType.TOO_MANY_ATTEMPTS,
                    "Too many failed attempts. Account temporarily locked. Try again later or reset your password.")

            // Network problem
            code.contains("NETWORK_REQUEST_FAILED", ignoreCase = true) ||
            code.contains("network-request-failed", ignoreCase = true) ->
                AuthError(AuthErrorType.NETWORK,
                    "Network error. Please check your internet connection and try again.")

            // Fallback
            else ->
                AuthError(AuthErrorType.GENERIC,
                    "Sign-in failed. Please check your credentials and try again.")
        }
    }

    // ──────────────────────────────────────────────
    // Session & Navigation
    // ──────────────────────────────────────────────

    private fun saveSessionAndNavigate(user: FirebaseUser?) {
        Toast.makeText(applicationContext, "Login successful!", Toast.LENGTH_LONG).show()
        val sharedPref = getSharedPreferences("user_session", Context.MODE_PRIVATE)
        with(sharedPref.edit()) {
            putBoolean("is_logged_in", true)
            putString("user_email", user?.email ?: "")
            putString("user_display_name", user?.displayName ?: "")
            putString("user_photo_url", user?.photoUrl?.toString() ?: "")
            apply()
        }

        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        super.onBackPressed()
        finishAffinity()
    }
}
