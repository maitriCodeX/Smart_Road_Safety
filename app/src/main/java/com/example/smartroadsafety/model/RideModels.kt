package com.example.smartroadsafety.model

data class NavigationAlert(
    val alertId: String,
    val title: String,
    val instruction: String,
    val severity: String, // HIGH, MEDIUM, LOW
    val distanceAheadMeters: Int,
    val category: String // ACCIDENT_PRONE, POTHOLE, BLIND_CURVE, SPEED_LIMIT
)

data class RideSession(
    val destination: String,
    val origin: String,
    val distanceKm: Double,
    val estimatedMins: Int,
    val alerts: List<NavigationAlert>
)
