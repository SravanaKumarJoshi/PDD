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
import com.biopolymer.screening.databinding.ActivitySignUpBinding
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.FirebaseUser
import com.google.firebase.auth.UserProfileChangeRequest

class SignUpActivity : AppCompatActivity() {

    companion object {
        private const val TAG = "SignUpActivity"
    }

    private lateinit var binding: ActivitySignUpBinding
    private lateinit var auth: FirebaseAuth

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        WindowCompat.setDecorFitsSystemWindows(window, false)
        binding = ActivitySignUpBinding.inflate(layoutInflater)
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
        binding.btnSignup.setOnClickListener {
            validateAndSignUp()
        }

        binding.tvLoginLink.setOnClickListener {
            finish() // Goes back to LoginActivity
        }
    }

    // ──────────────────────────────────────────────
    // Email/Password Sign Up
    // ──────────────────────────────────────────────

    private fun validateAndSignUp() {
        val name = binding.etName.text.toString().trim()
        val email = binding.etEmail.text.toString().trim()
        val password = binding.etPassword.text.toString().trim()
        val confirmPassword = binding.etConfirmPassword.text.toString().trim()

        var isValid = true

        if (name.isEmpty()) {
            binding.tilName.error = "Please enter your name"
            isValid = false
        } else {
            binding.tilName.error = null
        }

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

        if (confirmPassword != password) {
            binding.tilConfirmPassword.error = "Passwords do not match"
            isValid = false
        } else {
            binding.tilConfirmPassword.error = null
        }

        if (isValid) {
            performSignUp(name, email, password)
        }
    }

    private fun performSignUp(name: String, email: String, password: String) {
        binding.progressBar.visibility = View.VISIBLE
        binding.btnSignup.visibility = View.INVISIBLE

        auth.createUserWithEmailAndPassword(email, password)
            .addOnCompleteListener(this) { task ->
                if (task.isSuccessful) {
                    val user = auth.currentUser
                    val profileUpdates = UserProfileChangeRequest.Builder()
                        .setDisplayName(name)
                        .build()

                    user?.updateProfile(profileUpdates)
                        ?.addOnCompleteListener { profileTask ->
                            binding.progressBar.visibility = View.GONE
                            binding.btnSignup.visibility = View.VISIBLE
                            
                            if (profileTask.isSuccessful) {
                                Toast.makeText(applicationContext, "Account created successfully", Toast.LENGTH_LONG).show()
                                finish()
                            }
                        }
                } else {
                    binding.progressBar.visibility = View.GONE
                    binding.btnSignup.visibility = View.VISIBLE
                    Toast.makeText(this, "Registration failed: ${task.exception?.message}", 
                        Toast.LENGTH_LONG).show()
                }
            }
    }

    // ──────────────────────────────────────────────
    // Session & Navigation
    // ──────────────────────────────────────────────

    private fun saveSessionAndNavigate(user: FirebaseUser) {
        Toast.makeText(applicationContext, "Sign up successful!", Toast.LENGTH_LONG).show()
        val sharedPref = getSharedPreferences("user_session", Context.MODE_PRIVATE)
        with(sharedPref.edit()) {
            putBoolean("is_logged_in", true)
            putString("user_email", user.email ?: "")
            putString("user_display_name", user.displayName ?: "")
            putString("user_photo_url", user.photoUrl?.toString() ?: "")
            apply()
        }

        val intent = Intent(this, MainActivity::class.java)
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }
}
