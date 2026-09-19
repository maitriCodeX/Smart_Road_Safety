package com.example.smartroadsafety.model

data class RouteHazard(
    val hazardId: String,
    val hazardType: String, // POTHOLE, ACCIDENT_BLACKSPOT, BLIND_CURVE, WATER_LOGGING
    val title: String,
    val nearbyLocation: String,
    val description: String,
    val severity: String, // CRITICAL, MODERATE, LOW
    val lat: Double = 0.0,
    val lon: Double = 0.0
)

data class TravelRoute(
    val routeId: String,
    val title: String,
    val origin: String,
    val destination: String,
    val tripCount: Int,
    val totalDistanceKm: Double,
    val hazardsCount: Int,
    val hazards: List<RouteHazard>
)
