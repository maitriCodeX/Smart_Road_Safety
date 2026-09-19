package com.example.smartroadsafety.model

data class User(
    val userId: String,
    val name: String,
    val email: String
)

data class AuthResponse(
    val success: Boolean,
    val message: String,
    val token: String?,
    val user: User?
)
