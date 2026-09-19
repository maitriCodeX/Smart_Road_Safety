package com.example.smartroadsafety

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.widget.AppCompatButton
import com.example.smartroadsafety.data.DataRepository

class AuthActivity : AppCompatActivity() {

    private lateinit var tabLogin: TextView
    private lateinit var tabRegister: TextView
    private lateinit var tvCardSubtitle: TextView
    private lateinit var layoutLoginForm: LinearLayout
    private lateinit var layoutRegisterForm: LinearLayout

    // Login Fields
    private lateinit var etLoginEmail: EditText
    private lateinit var etLoginPassword: EditText
    private lateinit var btnLoginSubmit: AppCompatButton

    // Register Fields
    private lateinit var etRegisterName: EditText
    private lateinit var etRegisterEmail: EditText
    private lateinit var etRegisterPassword: EditText
    private lateinit var etRegisterConfirmPassword: EditText
    private lateinit var btnRegisterSubmit: AppCompatButton

    private var isLoginMode = true

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_auth)

        initViews()
        setupListeners()
    }

    private fun initViews() {
        tabLogin = findViewById(R.id.tabLogin)
        tabRegister = findViewById(R.id.tabRegister)
        tvCardSubtitle = findViewById(R.id.tvCardSubtitle)
        layoutLoginForm = findViewById(R.id.layoutLoginForm)
        layoutRegisterForm = findViewById(R.id.layoutRegisterForm)

        etLoginEmail = findViewById(R.id.etLoginEmail)
        etLoginPassword = findViewById(R.id.etLoginPassword)
        btnLoginSubmit = findViewById(R.id.btnLoginSubmit)

        etRegisterName = findViewById(R.id.etRegisterName)
        etRegisterEmail = findViewById(R.id.etRegisterEmail)
        etRegisterPassword = findViewById(R.id.etRegisterPassword)
        etRegisterConfirmPassword = findViewById(R.id.etRegisterConfirmPassword)
        btnRegisterSubmit = findViewById(R.id.btnRegisterSubmit)

        // Pre-fill demo login credentials for quick testing
        etLoginEmail.setText("rahul.sharma@example.com")
        etLoginPassword.setText("SecurePass@2026")
    }

    private fun setupListeners() {
        tabLogin.setOnClickListener {
            switchToLoginMode()
        }

        tabRegister.setOnClickListener {
            switchToRegisterMode()
        }

        btnLoginSubmit.setOnClickListener {
            handleLogin()
        }

        btnRegisterSubmit.setOnClickListener {
            handleRegister()
        }
    }

    private fun switchToLoginMode() {
        isLoginMode = true
        tabLogin.setBackgroundResource(R.drawable.bg_tab_selected)
        tabLogin.setTextColor(getColor(R.color.white))

        tabRegister.setBackgroundColor(getColor(R.color.transparent))
        tabRegister.setTextColor(getColor(R.color.black))

        tvCardSubtitle.text = "Sign in to your Telematics Dashboard"
        layoutLoginForm.visibility = View.VISIBLE
        layoutRegisterForm.visibility = View.GONE
    }

    private fun switchToRegisterMode() {
        isLoginMode = false
        tabRegister.setBackgroundResource(R.drawable.bg_tab_selected)
        tabRegister.setTextColor(getColor(R.color.white))

        tabLogin.setBackgroundColor(getColor(R.color.transparent))
        tabLogin.setTextColor(getColor(R.color.black))

        tvCardSubtitle.text = "Create your Smart Road Safety Account"
        layoutLoginForm.visibility = View.GONE
        layoutRegisterForm.visibility = View.VISIBLE
    }

    private fun handleRegister() {
        val name = etRegisterName.text.toString().trim()
        val email = etRegisterEmail.text.toString().trim()
        val password = etRegisterPassword.text.toString().trim()
        val confirmPassword = etRegisterConfirmPassword.text.toString().trim()

        if (name.isEmpty()) {
            etRegisterName.error = "Name is required"
            etRegisterName.requestFocus()
            return
        }

        if (email.isEmpty() || !android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
            etRegisterEmail.error = "Enter a valid email"
            etRegisterEmail.requestFocus()
            return
        }

        if (password.length < 6) {
            etRegisterPassword.error = "Password must be at least 6 characters"
            etRegisterPassword.requestFocus()
            return
        }

        if (password != confirmPassword) {
            etRegisterConfirmPassword.error = "Passwords do not match"
            etRegisterConfirmPassword.requestFocus()
            return
        }

        // Save registration
        DataRepository.register(name, email, password)

        Toast.makeText(this, "Registration successful! Please login.", Toast.LENGTH_LONG).show()

        // Per requirements: "After user register themself they should be redirected to login and should login."
        switchToLoginMode()
        etLoginEmail.setText(email)
        etLoginPassword.setText(password)
        etLoginPassword.requestFocus()
    }

    private fun handleLogin() {
        val email = etLoginEmail.text.toString().trim()
        val password = etLoginPassword.text.toString().trim()

        if (email.isEmpty()) {
            etLoginEmail.error = "Email is required"
            etLoginEmail.requestFocus()
            return
        }

        if (password.isEmpty()) {
            etLoginPassword.error = "Password is required"
            etLoginPassword.requestFocus()
            return
        }

        val success = DataRepository.login(email, password)
        if (success) {
            Toast.makeText(this, "Welcome to Smart Road Safety!", Toast.LENGTH_SHORT).show()
            val intent = Intent(this, MainActivity::class.java)
            startActivity(intent)
            finish()
        } else {
            Toast.makeText(this, "Invalid email or password", Toast.LENGTH_SHORT).show()
        }
    }
}
