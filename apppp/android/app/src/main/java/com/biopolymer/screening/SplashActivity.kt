package com.biopolymer.screening

import android.annotation.SuppressLint
import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.ViewCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import com.biopolymer.screening.databinding.ActivitySplashBinding
import com.google.firebase.auth.FirebaseAuth

@SuppressLint("CustomSplashScreen")
class SplashActivity : AppCompatActivity() {

    private lateinit var binding: ActivitySplashBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        WindowCompat.setDecorFitsSystemWindows(window, false)
        binding = ActivitySplashBinding.inflate(layoutInflater)
        setContentView(binding.root)

        ViewCompat.setOnApplyWindowInsetsListener(binding.root) { view, insets ->
            val systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom)
            insets
        }

        Handler(Looper.getMainLooper()).postDelayed({
            checkLoginState()
        }, 2500)
    }

    private fun checkLoginState() {
        // Check both Firebase Auth state (covers Google Sign-In persistence)
        // and SharedPreferences (covers email/password sign-in persistence).
        val firebaseUser = FirebaseAuth.getInstance().currentUser
        val sharedPref = getSharedPreferences("user_session", Context.MODE_PRIVATE)
        val isLoggedIn = sharedPref.getBoolean("is_logged_in", false)

        if (firebaseUser != null || isLoggedIn) {
            // If Firebase has a user but SharedPreferences doesn't (e.g. app data cleared
            // partially), sync the session state so downstream code can rely on SharedPrefs.
            if (firebaseUser != null && !isLoggedIn) {
                with(sharedPref.edit()) {
                    putBoolean("is_logged_in", true)
                    putString("user_email", firebaseUser.email ?: "")
                    putString("user_display_name", firebaseUser.displayName ?: "")
                    putString("user_photo_url", firebaseUser.photoUrl?.toString() ?: "")
                    apply()
                }
            }
            startActivity(Intent(this, MainActivity::class.java))
        } else {
            startActivity(Intent(this, LoginActivity::class.java))
        }
        finish()
    }
}
