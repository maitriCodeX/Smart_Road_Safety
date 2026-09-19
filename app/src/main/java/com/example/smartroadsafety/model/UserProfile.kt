package com.example.smartroadsafety.model

data class UserProfile(
    val userId: String,
    val name: String,
    val profilePictureUrl: String = "",
    val email: String,
    val password: String,
    val phoneNumber: String,
    val relativePhoneNumber: String,
    val age: Int,
    val bloodGroup: String,
    val carPlateNumber: String
)
