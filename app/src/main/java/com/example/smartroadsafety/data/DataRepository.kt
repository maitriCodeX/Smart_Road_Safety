package com.example.smartroadsafety.data

import com.example.smartroadsafety.model.*

object DataRepository {

    // Registered users placeholder
    private val registeredUsers = mutableMapOf<String, String>(
        "demo@smartroadsafety.com" to "password123",
        "rahul.sharma@example.com" to "SecurePass@2026"
    )

    private var currentUser: User? = User("USR_98241", "Rahul Sharma", "rahul.sharma@example.com")

    // User Profile Placeholder
    private var userProfile = UserProfile(
        userId = "USR_98241",
        name = "Rahul Sharma",
        profilePictureUrl = "",
        email = "rahul.sharma@example.com",
        password = "SecurePass@2026",
        phoneNumber = "+91 98765 43210",
        relativePhoneNumber = "+91 91234 56789",
        age = 24,
        bloodGroup = "B+",
        carPlateNumber = "GJ-01-AB-1234"
    )

    // Frequently Traveled Routes with route-specific hazards
    private val travelRoutes = listOf(
        TravelRoute(
            routeId = "ROUTE_GNR_MEH",
            title = "Gandhinagar to Mehsana",
            origin = "Gandhinagar CH Road",
            destination = "Mehsana Highway Bypass",
            tripCount = 34,
            totalDistanceKm = 68.5,
            hazardsCount = 4,
            hazards = listOf(
                RouteHazard(
                    hazardId = "HAZ_01",
                    hazardType = "POTHOLE",
                    title = "Severe Pothole Cluster",
                    nearbyLocation = "Near: 50m past S-DMart, Kudasan Crossroad",
                    description = "Multiple deep edge fractures and craters detected by IMU jerk sensor (Δa/Δt > 15 m/s³).",
                    severity = "CRITICAL",
                    lat = 23.1894,
                    lon = 72.6281
                ),
                RouteHazard(
                    hazardId = "HAZ_02",
                    hazardType = "ACCIDENT_BLACKSPOT",
                    title = "High Crash Risk Intersection",
                    nearbyLocation = "Near: Chhatral GIDC Junction (Palanpur Highway)",
                    description = "Frequent commercial trailer crossing. Speed limit strictly geofenced to 35 km/h.",
                    severity = "CRITICAL",
                    lat = 23.3120,
                    lon = 72.4410
                ),
                RouteHazard(
                    hazardId = "HAZ_03",
                    hazardType = "BLIND_CURVE",
                    title = "Blind Curve & Narrow Shoulder",
                    nearbyLocation = "Near: Narmada Canal Bridge Crossing, Sector 28",
                    description = "Sharp curve with obstructed visibility. High lateral swerve risk.",
                    severity = "MODERATE",
                    lat = 23.2512,
                    lon = 72.6450
                ),
                RouteHazard(
                    hazardId = "HAZ_04",
                    hazardType = "WATER_LOGGING",
                    title = "Slippery Road / Water Logging Area",
                    nearbyLocation = "Near: Mehsana Southern Toll Plaza underpass",
                    description = "Reduced tire traction during evening humidity and seasonal water logging.",
                    severity = "MODERATE",
                    lat = 23.5821,
                    lon = 72.3912
                )
            )
        ),
        TravelRoute(
            routeId = "ROUTE_GNR_AHD",
            title = "Gandhinagar to Ahmedabad",
            origin = "Sector 7, Gandhinagar",
            destination = "Iskcon Crossroad, SG Highway",
            tripCount = 52,
            totalDistanceKm = 32.4,
            hazardsCount = 3,
            hazards = listOf(
                RouteHazard(
                    hazardId = "HAZ_11",
                    hazardType = "ACCIDENT_BLACKSPOT",
                    title = "Severe Blackspot Zone",
                    nearbyLocation = "Near: Vaishno Devi Circle Flyover entry",
                    description = "Heavy convergence zone. 38 crashes recorded; regulatory limit drops to 40 km/h.",
                    severity = "CRITICAL",
                    lat = 23.1368,
                    lon = 72.5489
                ),
                RouteHazard(
                    hazardId = "HAZ_12",
                    hazardType = "POTHOLE",
                    title = "Deep Road Depression",
                    nearbyLocation = "Near: Gota Bridge service road exit",
                    description = "Sunken road trench near drainage cover causing sudden deceleration shocks.",
                    severity = "MODERATE",
                    lat = 23.0945,
                    lon = 72.5350
                ),
                RouteHazard(
                    hazardId = "HAZ_13",
                    hazardType = "ACCIDENT_BLACKSPOT",
                    title = "Pedestrian & Commercial Vehicle Conflict Zone",
                    nearbyLocation = "Near: Iskcon Crossroad BRTS Corridor",
                    description = "Historical high-fatality blackspot. Rapid lane changing penalties active.",
                    severity = "CRITICAL",
                    lat = 23.0298,
                    lon = 72.5074
                )
            )
        ),
        TravelRoute(
            routeId = "ROUTE_AHD_SNND",
            title = "Ahmedabad to Sanand",
            origin = "Bopal Ring Road",
            destination = "Sanand GIDC Industrial Gate",
            tripCount = 19,
            totalDistanceKm = 24.8,
            hazardsCount = 2,
            hazards = listOf(
                RouteHazard(
                    hazardId = "HAZ_21",
                    hazardType = "ACCIDENT_BLACKSPOT",
                    title = "Sarkhej-Sanand High Speed Blackspot",
                    nearbyLocation = "Near: Sanand Highway Overbridge (Near Tata Motors)",
                    description = "High-speed freight corridor with unlit divider cuts.",
                    severity = "CRITICAL",
                    lat = 22.9856,
                    lon = 72.3789
                ),
                RouteHazard(
                    hazardId = "HAZ_22",
                    hazardType = "POTHOLE",
                    title = "Industrial Heavy Truck Rutting & Potholes",
                    nearbyLocation = "Near: Telav Crossroad, 200m before Petrol Pump",
                    description = "Surface deformation caused by heavy axle loading.",
                    severity = "MODERATE",
                    lat = 22.9980,
                    lon = 72.4350
                )
            )
        )
    )

    // Driver Score & Fine Tickets Placeholder
    private var driverScoreSummary = DriverScoreSummary(
        overallScore = 88,
        actuarialTier = "Platinum Safe",
        insuranceDiscountPct = 25,
        trend = "IMPROVING",
        pillars = TelematicsPillars(
            smoothnessPct = 92,
            corneringPct = 85,
            speedCompliancePct = 88,
            vigilancePct = 84
        ),
        fineTickets = listOf(
            FineTicket(
                ticketId = "TCK-2026-901",
                reason = "Overspeeding > 80 km/h at SG Highway",
                date = "18 Sep 2026, 04:15 PM",
                amount = "₹1,000",
                status = "UNPAID",
                location = "SG Highway Flyover near Vaishno Devi"
            ),
            FineTicket(
                ticketId = "TCK-2026-842",
                reason = "Red Light Violation at Iskcon Crossroad",
                date = "12 Sep 2026, 09:30 AM",
                amount = "₹1,500",
                status = "UNPAID",
                location = "Iskcon Crossroad Traffic Signal"
            ),
            FineTicket(
                ticketId = "TCK-2026-789",
                reason = "Harsh Lane Changing & Tailgating",
                date = "04 Sep 2026, 07:10 PM",
                amount = "₹500",
                status = "UNPAID",
                location = "Gandhinagar Koba Circle Expressway"
            )
        )
    )

    // Heatmap data placeholder
    private val heatmapOverview = HeatmapOverview(
        totalIncidents = 132,
        centerLat = 23.1124,
        centerLon = 72.5489,
        points = listOf(
            HeatmapPoint(23.0298, 72.5074, 0.95, "Iskcon Crossroad Blackspot"),
            HeatmapPoint(23.1368, 72.5489, 0.90, "Vaishno Devi Circle"),
            HeatmapPoint(22.9856, 72.3789, 0.85, "Sarkhej-Sanand Corridor"),
            HeatmapPoint(22.9821, 72.5934, 0.82, "Narol Industrial Circle"),
            HeatmapPoint(23.3120, 72.4410, 0.88, "Chhatral GIDC Junction"),
            HeatmapPoint(23.5821, 72.3912, 0.78, "Mehsana Bypass Blackspot")
        ),
        blackspots = listOf(
            BlackspotZone("BS-01", "Iskcon Crossroad", 23.0298, 72.5074, 250.0, "#9D0208", 42, 7, 35),
            BlackspotZone("BS-02", "Vaishno Devi Circle", 23.1368, 72.5489, 300.0, "#9D0208", 38, 5, 40),
            BlackspotZone("BS-03", "Chhatral GIDC Highway", 23.3120, 72.4410, 200.0, "#9D0208", 29, 4, 35),
            BlackspotZone("BS-04", "Sarkhej-Sanand Crossroad", 22.9856, 72.3789, 350.0, "#9D0208", 31, 6, 40)
        )
    )

    // Auth methods
    fun register(name: String, email: String, pass: String): Boolean {
        registeredUsers[email] = pass
        currentUser = User("USR_${System.currentTimeMillis() % 100000}", name, email)
        userProfile = userProfile.copy(name = name, email = email, password = pass)
        return true
    }

    fun login(email: String, pass: String): Boolean {
        // Accept registered user, demo account or any validly formatted credential
        val storedPass = registeredUsers[email]
        if (storedPass != null && storedPass == pass) {
            currentUser = User("USR_${System.currentTimeMillis() % 100000}", userProfile.name, email)
            return true
        }
        if (email.isNotEmpty() && pass.isNotEmpty()) {
            currentUser = User("USR_${System.currentTimeMillis() % 100000}", userProfile.name, email)
            return true
        }
        return false
    }

    fun getCurrentUser(): User? = currentUser

    // Ride Navigation
    fun getAlertsForDestination(destination: String): List<NavigationAlert> {
        return listOf(
            NavigationAlert(
                alertId = "ALT-001",
                title = "Accident Prone Area Ahead",
                instruction = "Navigation and alert instruction: High crash zone near Vaishno Devi circle. Reduce speed to 35 km/h.",
                severity = "HIGH",
                distanceAheadMeters = 350,
                category = "ACCIDENT_PRONE"
            ),
            NavigationAlert(
                alertId = "ALT-002",
                title = "Pothole Cluster 200m Ahead",
                instruction = "Navigation and alert instruction: Multiple sharp surface craters on right lane. Shift to center lane cautiously.",
                severity = "HIGH",
                distanceAheadMeters = 200,
                category = "POTHOLE"
            ),
            NavigationAlert(
                alertId = "ALT-003",
                title = "Blind Curve & Speed Limit Warning",
                instruction = "Navigation and alert instruction: Sharp blind hairpin curve 500m ahead. Speed limit restricted to 40 km/h.",
                severity = "MEDIUM",
                distanceAheadMeters = 500,
                category = "BLIND_CURVE"
            ),
            NavigationAlert(
                alertId = "ALT-004",
                title = "Speed Camera Geofence Active",
                instruction = "Navigation and alert instruction: Automated telematics radar enforcement active. Maintain safe deceleration buffer.",
                severity = "LOW",
                distanceAheadMeters = 800,
                category = "SPEED_LIMIT"
            )
        )
    }

    // Hazards
    fun getFrequentlyTraveledRoutes(): List<TravelRoute> = travelRoutes

    fun getHazardsForRoute(routeId: String): List<RouteHazard> {
        return travelRoutes.find { it.routeId == routeId }?.hazards ?: emptyList()
    }

    fun getRouteById(routeId: String): TravelRoute? {
        return travelRoutes.find { it.routeId == routeId }
    }

    // Driver score & Fine tickets
    fun getDriverScoreSummary(): DriverScoreSummary = driverScoreSummary

    // Heatmap
    fun getHeatmapOverview(): HeatmapOverview = heatmapOverview

    // Profile
    fun getUserProfile(): UserProfile = userProfile

    fun updateUserProfile(updated: UserProfile) {
        userProfile = updated
    }
}
