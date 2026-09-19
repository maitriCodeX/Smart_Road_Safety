package com.example.smartroadsafety.model

data class HeatmapPoint(
    val lat: Double,
    val lon: Double,
    val weight: Double,
    val locationName: String
)

data class BlackspotZone(
    val id: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    val radiusM: Double,
    val color: String,
    val historicalCrashes: Int,
    val fatalities: Int,
    val speedLimitKmh: Int
)

data class HeatmapOverview(
    val totalIncidents: Int,
    val centerLat: Double,
    val centerLon: Double,
    val points: List<HeatmapPoint>,
    val blackspots: List<BlackspotZone>
)
