package com.example.smartroadsafety.data

import android.util.Log
import com.example.smartroadsafety.SafetyEngine
import com.example.smartroadsafety.model.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

object DataRepository {

    private const val TAG = "DataRepository"

    private var authToken: String? = null
    private var currentUser: User? = User("USR_98241", "Rahul Sharma", "rahul.sharma@example.com")

    // In-memory cache for instant UI rendering and offline fallback
    private var userProfile = UserProfile(
        userId = "USR_98241",
        name = "Rahul Sharma",
        profilePictureUrl = "",
        email = "rahul.sharma@example.com",
        password = "SecurePass@2026",
        phoneNumber = "+91 98765 43210",
        relativePhoneNumber = "+919726222922",
        age = 24,
        bloodGroup = "B+",
        carPlateNumber = "GJ-01-AB-1234"
    )

    private var travelRoutes = listOf(
        TravelRoute(
            routeId = "ROUTE_GNR_MEH_01",
            title = "Gandhinagar to Mehsana",
            origin = "Gandhinagar CH Road",
            destination = "Mehsana Highway Circle",
            tripCount = 28,
            totalDistanceKm = 68.5,
            hazardsCount = 6,
            hazards = listOf(
                RouteHazard("HAZ_01", "POTHOLE", "Severe Pothole Cluster", "Chhatral GIDC Highway", "Deep road depression in high-speed corridor.", "HIGH", 23.3120, 72.4410),
                RouteHazard("HAZ_02", "ACCIDENT_BLACKSPOT", "Nandasan High Crash Junction", "Nandasan Crossroad", "Frequent freight collisions recorded.", "HIGH", 23.3890, 72.4120),
                RouteHazard("HAZ_03", "SHARP_CURVE", "Unbanked Curve Warning", "Near Mehsana Highway Toll", "Blind corner prone to heavy vehicle skidding.", "MODERATE", 23.4750, 72.3900),
                RouteHazard("HAZ_04", "ROAD_WORK", "Canal Overpass Construction", "Kadi Branch Canal", "Lane constriction with irregular asphalt gravel.", "MODERATE", 23.2800, 72.4600),
                RouteHazard("HAZ_05", "ROAD_DEFECT", "Severe Rutting & Water Hazard", "Kalol Bypass Stretch", "Deep asphalt ruts causing aquaplaning risk.", "LOW", 23.3400, 72.4250),
                RouteHazard("HAZ_06", "ACCIDENT_BLACKSPOT", "Freight Merge Danger Zone", "Mehsana Outer Ring", "Heavy freight trucks turning across high-speed lane.", "HIGH", 23.5100, 72.3800)
            )
        ),
        TravelRoute(
            routeId = "ROUTE_AHM_GNR_02",
            title = "Ahmedabad to Gandhinagar",
            origin = "Iskcon Crossroad, SG Highway",
            destination = "Infocity, Gandhinagar",
            tripCount = 45,
            totalDistanceKm = 26.3,
            hazardsCount = 5,
            hazards = listOf(
                RouteHazard("HAZ_11", "ACCIDENT_BLACKSPOT", "Vaishno Devi Circle Ramp", "SG Highway Overpass", "Collision-prone merge ramp with high traffic density.", "HIGH", 23.1368, 72.5489),
                RouteHazard("HAZ_12", "POTHOLE", "Asphalt Deformation near Nirma", "Opposite Nirma University", "Sunken road section causing abrupt lane departure.", "MODERATE", 23.1250, 72.5410),
                RouteHazard("HAZ_13", "ACCIDENT_BLACKSPOT", "Bhaijipura Traffic Chokepoint", "Koba-Gandhinagar Road", "Frequent sudden braking incidents at signal.", "HIGH", 23.1670, 72.5890),
                RouteHazard("HAZ_14", "ROAD_DEFECT", "Infocity Entry Expansion Joint", "Infocity IT Park Gate", "Damaged road expansion joint causing vehicle bounce.", "LOW", 23.1900, 72.6200),
                RouteHazard("HAZ_15", "PEDESTRIAN_ZONE", "Jaywalking Hotspot", "Near PDPU Junction", "High student footfall crossing unbarricaded road.", "MODERATE", 23.1550, 72.6650)
            )
        ),
        TravelRoute(
            routeId = "ROUTE_AHM_SND_03",
            title = "Ahmedabad to Sanand Corridor",
            origin = "Bopal Ring Road",
            destination = "Sanand GIDC Gateway",
            tripCount = 18,
            totalDistanceKm = 24.8,
            hazardsCount = 4,
            hazards = listOf(
                RouteHazard("HAZ_21", "ACCIDENT_BLACKSPOT", "Sarkhej-Sanand Freight Merge", "Sanand Highway km 12", "Heavy industrial traffic merging without acceleration lane.", "HIGH", 22.9856, 72.3789),
                RouteHazard("HAZ_22", "POTHOLE", "Shoulder Erosion & Potholes", "Sanand GIDC Phase 2", "Unpaved road shoulder with sharp asphalt edge drops.", "HIGH", 22.9650, 72.3450),
                RouteHazard("HAZ_23", "ACCIDENT_BLACKSPOT", "Bopal Ring Road Intersection", "South Bopal Flyover Ramp", "High collision frequency during evening peak hours.", "MODERATE", 23.0340, 72.4650),
                RouteHazard("HAZ_24", "ROAD_WORK", "Telav Canal Bridge Repairs", "Telav Approach Road", "Single lane traffic bypass over canal culvert.", "MODERATE", 23.0100, 72.4100)
            )
        )
    )

    private var driverScoreSummary = DriverScoreSummary(
        overallScore = 100,
        actuarialTier = "Platinum Safe",
        insuranceDiscountPct = 25,
        trend = "STABLE",
        pillars = TelematicsPillars(
            smoothnessPct = 100,
            corneringPct = 100,
            speedCompliancePct = 100,
            vigilancePct = 97
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
            )
        )
    )

    private var heatmapOverview = HeatmapOverview(
        totalIncidents = 137,
        centerLat = 23.1124,
        centerLon = 72.5489,
        points = listOf(
            HeatmapPoint(23.0298, 72.5074, 1.0, "Accident Hotspot Cluster"),
            HeatmapPoint(23.1368, 72.5489, 0.90, "Vaishno Devi Circle"),
            HeatmapPoint(23.3120, 72.4410, 0.88, "Chhatral GIDC Highway"),
            HeatmapPoint(22.9856, 72.3789, 0.85, "Sarkhej-Sanand Corridor")
        ),
        blackspots = listOf(
            BlackspotZone("BS_001", "SG Highway - Iskcon Crossroad Overpass", 23.0298, 72.5074, 180.0, "#9D0208", 42, 8, 50),
            BlackspotZone("BS_002", "Vaishno Devi Circle Flyover Ramp", 23.1368, 72.5489, 200.0, "#9D0208", 38, 6, 40),
            BlackspotZone("BS_003", "Chhatral GIDC Highway Crossing", 23.3120, 72.4410, 220.0, "#9D0208", 29, 4, 35),
            BlackspotZone("BS_004", "Sanand Highway Heavy Freight Junction", 22.9856, 72.3789, 250.0, "#9D0208", 31, 7, 45)
        )
    )

    // ========================================================
    // HTTP CLIENT ENGINE
    // ========================================================

    private suspend fun httpGet(endpoint: String): Pair<Int, String> = withContext(Dispatchers.IO) {
        var conn: HttpURLConnection? = null
        try {
            val base = SafetyEngine.resolveBaseUrl().trimEnd('/')
            val fullUrl = if (endpoint.startsWith("http")) endpoint else "$base$endpoint"
            val url = URL(fullUrl)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "GET"
            conn.setRequestProperty("Bypass-Tunnel-Reminder", "true")
            conn.setRequestProperty("User-Agent", "SmartRoadSafety/1.0")
            authToken?.let { conn.setRequestProperty("Authorization", "Bearer $it") }
            conn.connectTimeout = 7000
            conn.readTimeout = 7000

            val code = conn.responseCode
            val body = if (code in 200..299) {
                conn.inputStream.bufferedReader().use { it.readText() }
            } else {
                conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
            }
            Pair(code, body)
        } catch (e: Exception) {
            Log.w(TAG, "GET $endpoint failed: ${e.message}")
            Pair(-1, e.message ?: "Network error")
        } finally {
            conn?.disconnect()
        }
    }

    private suspend fun httpPost(endpoint: String, jsonPayload: String): Pair<Int, String> = withContext(Dispatchers.IO) {
        var conn: HttpURLConnection? = null
        try {
            val base = SafetyEngine.resolveBaseUrl().trimEnd('/')
            val fullUrl = if (endpoint.startsWith("http")) endpoint else "$base$endpoint"
            val url = URL(fullUrl)
            conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            conn.setRequestProperty("Bypass-Tunnel-Reminder", "true")
            conn.setRequestProperty("User-Agent", "SmartRoadSafety/1.0")
            authToken?.let { conn.setRequestProperty("Authorization", "Bearer $it") }
            conn.connectTimeout = 7000
            conn.readTimeout = 7000
            conn.doOutput = true

            val bytes = jsonPayload.toByteArray(Charsets.UTF_8)
            conn.setFixedLengthStreamingMode(bytes.size)
            conn.outputStream.use { it.write(bytes) }

            val code = conn.responseCode
            val body = if (code in 200..299) {
                conn.inputStream.bufferedReader().use { it.readText() }
            } else {
                conn.errorStream?.bufferedReader()?.use { it.readText() } ?: ""
            }
            Pair(code, body)
        } catch (e: Exception) {
            Log.w(TAG, "POST $endpoint failed: ${e.message}")
            Pair(-1, e.message ?: "Network error")
        } finally {
            conn?.disconnect()
        }
    }

    // ========================================================
    // 1. AUTHENTICATION
    // ========================================================

    suspend fun loginOnline(email: String, pass: String): Pair<Boolean, String> {
        val payload = JSONObject().apply {
            put("email", email.trim())
            put("password", pass.trim())
        }
        val (code, body) = httpPost("/api/auth/login", payload.toString())
        if (code in 200..299 && body.isNotEmpty()) {
            return try {
                val json = JSONObject(body)
                val success = json.optBoolean("success", true)
                if (success) {
                    authToken = json.optString("token", "")
                    val userObj = json.optJSONObject("user")
                    if (userObj != null) {
                        currentUser = User(
                            userId = userObj.optString("user_id", "USR_98241"),
                            name = userObj.optString("name", "User"),
                            email = userObj.optString("email", email)
                        )
                    }
                    Pair(true, json.optString("message", "Login successful"))
                } else {
                    Pair(false, json.optString("message", "Invalid credentials"))
                }
            } catch (e: Exception) {
                Pair(false, "Invalid response from server")
            }
        }
        // Fallback check: if server has temporary tunnel issue, allow offline demo credentials
        if (code !in 200..299 && code != 401) {
            val localValid = login(email, pass)
            if (localValid) {
                return Pair(true, "Signed in (Offline Cache Active)")
            }
        }
        val errorMsg = if (code == 401) "Invalid email or password" else "Server connection error (HTTP $code)"
        return Pair(false, errorMsg)
    }

    suspend fun registerOnline(name: String, email: String, pass: String, confirmPass: String): Pair<Boolean, String> {
        val payload = JSONObject().apply {
            put("name", name.trim())
            put("email", email.trim())
            put("password", pass.trim())
            put("confirm_password", confirmPass.trim())
        }
        val (code, body) = httpPost("/api/auth/register", payload.toString())
        if (code in 200..299 && body.isNotEmpty()) {
            return try {
                val json = JSONObject(body)
                val success = json.optBoolean("success", true)
                Pair(success, json.optString("message", "Registration successful"))
            } catch (e: Exception) {
                Pair(false, "Invalid server response")
            }
        }
        // Fallback check
        register(name, email, pass)
        return Pair(true, "Registration saved locally (Offline)")
    }

    // ========================================================
    // 2. USER PROFILE & EMERGENCY CONTACT
    // ========================================================

    suspend fun fetchUserProfileOnline(): UserProfile {
        val (code, body) = httpGet("/api/user/profile")
        if (code in 200..299 && body.isNotEmpty()) {
            try {
                val json = JSONObject(body)
                val relative = json.optString("relative_phone_number", userProfile.relativePhoneNumber)
                userProfile = UserProfile(
                    userId = json.optString("user_id", userProfile.userId),
                    name = json.optString("name", userProfile.name),
                    profilePictureUrl = json.optString("profile_picture_url", ""),
                    email = json.optString("email", userProfile.email),
                    password = userProfile.password,
                    phoneNumber = json.optString("phone_number", userProfile.phoneNumber),
                    relativePhoneNumber = relative,
                    age = json.optInt("age", userProfile.age),
                    bloodGroup = json.optString("blood_group", userProfile.bloodGroup),
                    carPlateNumber = json.optString("car_plate_number", userProfile.carPlateNumber)
                )
                if (relative.isNotBlank()) {
                    SafetyEngine.setEmergencyTargetPhone(relative)
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing user profile: ${e.message}")
            }
        }
        return userProfile
    }

    suspend fun updateUserProfileOnline(updated: UserProfile): Pair<Boolean, String> {
        userProfile = updated
        val payload = JSONObject().apply {
            put("email", updated.email)
            put("password", updated.password)
            put("phone_number", updated.phoneNumber)
            put("relative_phone_number", updated.relativePhoneNumber)
            put("age", updated.age)
            put("blood_group", updated.bloodGroup)
            put("car_plate_number", updated.carPlateNumber)
        }
        if (updated.relativePhoneNumber.isNotBlank()) {
            SafetyEngine.setEmergencyTargetPhone(updated.relativePhoneNumber)
        }
        val (code, body) = httpPost("/api/user/profile", payload.toString())
        return if (code in 200..299) {
            Pair(true, "Profile saved to backend successfully")
        } else {
            Pair(false, "Server update note: HTTP $code")
        }
    }

    // ========================================================
    // 3. RIDE NAVIGATION & HAZARD ALERTS
    // ========================================================

    suspend fun startRideOnline(destination: String, lat: Double, lon: Double): RideSession {
        val payload = JSONObject().apply {
            put("destination", destination)
            put("current_lat", lat)
            put("current_lon", lon)
        }

        var (code, body) = httpPost("/api/ride/start", payload.toString())
        if (code !in 200..299) {
            val navResult = httpGet("/api/navigation/alerts")
            if (navResult.first in 200..299) {
                code = navResult.first
                body = navResult.second
            }
        }

        if (code in 200..299 && body.isNotEmpty()) {
            try {
                val json = JSONObject(body)
                val alertsArr = json.optJSONArray("alerts") ?: JSONArray()
                val alertList = mutableListOf<NavigationAlert>()
                for (i in 0 until alertsArr.length()) {
                    val a = alertsArr.getJSONObject(i)
                    alertList.add(
                        NavigationAlert(
                            alertId = a.optString("alert_id", "ALT-$i"),
                            title = a.optString("title", "Road Hazard"),
                            instruction = a.optString("instruction", "Proceed with caution"),
                            severity = a.optString("severity", "HIGH"),
                            distanceAheadMeters = a.optInt("distance_ahead_m", a.optInt("distanceAheadMeters", 200)),
                            category = a.optString("category", "POTHOLE")
                        )
                    )
                }

                return RideSession(
                    destination = json.optString("destination", destination),
                    origin = json.optString("origin", "Infocity, Gandhinagar"),
                    distanceKm = json.optDouble("distance_km", 54.2),
                    estimatedMins = json.optInt("estimated_time_mins", json.optInt("estimated_mins", 58)),
                    alerts = alertList
                )
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing ride session: ${e.message}")
            }
        }

        // Fallback to offline alerts
        return RideSession(
            destination = destination,
            origin = "Gandhinagar CH Road",
            distanceKm = 54.0,
            estimatedMins = 58,
            alerts = getAlertsForDestination(destination)
        )
    }

    // ========================================================
    // 4. FREQUENT ROUTES & ROUTE HAZARDS
    // ========================================================

    suspend fun fetchFrequentRoutesOnline(): List<TravelRoute> {
        val (code, body) = httpGet("/api/hazards/frequent-routes")
        if (code in 200..299 && body.isNotEmpty()) {
            try {
                val arr = JSONArray(body)
                val routes = mutableListOf<TravelRoute>()
                for (i in 0 until arr.length()) {
                    val r = arr.getJSONObject(i)
                    routes.add(
                        TravelRoute(
                            routeId = r.optString("route_id", "ROUTE_$i"),
                            title = r.optString("title", "Route $i"),
                            origin = r.optString("origin", "Origin"),
                            destination = r.optString("destination", "Destination"),
                            tripCount = r.optInt("trip_count", 10),
                            totalDistanceKm = r.optDouble("total_distance_km", 25.0),
                            hazardsCount = r.optInt("total_hazards_count", r.optInt("hazardsCount", 0)),
                            hazards = emptyList()
                        )
                    )
                }
                if (routes.isNotEmpty()) {
                    travelRoutes = routes
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing frequent routes: ${e.message}")
            }
        }
        return travelRoutes
    }

    suspend fun fetchRouteHazardsOnline(routeId: String): List<RouteHazard> {
        val (code, body) = httpGet("/api/hazards/route-detail?route_id=$routeId")
        if (code in 200..299 && body.isNotEmpty()) {
            try {
                val json = JSONObject(body)
                val hazardsArr = json.optJSONArray("hazards") ?: JSONArray()
                val list = mutableListOf<RouteHazard>()
                for (i in 0 until hazardsArr.length()) {
                    val h = hazardsArr.getJSONObject(i)
                    list.add(
                        RouteHazard(
                            hazardId = h.optString("hazard_id", "HAZ_$i"),
                            hazardType = h.optString("hazard_type", "POTHOLE"),
                            title = h.optString("title", "Hazard"),
                            nearbyLocation = h.optString("nearby_location", ""),
                            description = h.optString("description", ""),
                            severity = h.optString("severity", "MODERATE"),
                            lat = h.optDouble("lat", 0.0),
                            lon = h.optDouble("lon", 0.0)
                        )
                    )
                }
                return list
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing route hazards: ${e.message}")
            }
        }
        return getHazardsForRoute(routeId)
    }

    // ========================================================
    // 5. DRIVER SAFETY SCORE & FINE TICKETS
    // ========================================================

    suspend fun fetchDriverScoreOnline(): DriverScoreSummary {
        val (code, body) = httpGet("/api/driver/score")
        if (code in 200..299 && body.isNotEmpty()) {
            try {
                val json = JSONObject(body)
                val pillarsObj = json.optJSONObject("pillars") ?: JSONObject()
                val ticketsArr = json.optJSONArray("fine_tickets") ?: JSONArray()

                val tickets = mutableListOf<FineTicket>()
                for (i in 0 until ticketsArr.length()) {
                    val t = ticketsArr.getJSONObject(i)
                    tickets.add(
                        FineTicket(
                            ticketId = t.optString("ticket_id", "TCK-$i"),
                            reason = t.optString("reason", "Violation"),
                            date = t.optString("date", ""),
                            amount = t.optString("amount", "₹500"),
                            status = t.optString("status", "UNPAID"),
                            location = t.optString("location", "")
                        )
                    )
                }

                driverScoreSummary = DriverScoreSummary(
                    overallScore = json.optInt("overall_score", 100),
                    actuarialTier = json.optString("actuarial_tier", "Platinum Safe"),
                    insuranceDiscountPct = json.optInt("insurance_discount_pct", 25),
                    trend = json.optString("trend", "STABLE"),
                    pillars = TelematicsPillars(
                        smoothnessPct = pillarsObj.optInt("smoothness_pct", 100),
                        corneringPct = pillarsObj.optInt("cornering_pct", 100),
                        speedCompliancePct = pillarsObj.optInt("speed_compliance_pct", 100),
                        vigilancePct = pillarsObj.optInt("vigilance_pct", 97)
                    ),
                    fineTickets = tickets
                )
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing driver score: ${e.message}")
            }
        }
        return driverScoreSummary
    }

    // ========================================================
    // 6. HEATMAP & BLACKSPOTS
    // ========================================================

    suspend fun fetchHeatmapOverviewOnline(): HeatmapOverview {
        val (hmCode, hmBody) = httpGet("/api/heatmap")
        val (bsCode, bsBody) = httpGet("/api/risk/blackspots")

        val pointsList = mutableListOf<HeatmapPoint>()
        var totalIncidents = heatmapOverview.totalIncidents
        var centerLat = heatmapOverview.centerLat
        var centerLon = heatmapOverview.centerLon

        if (hmCode in 200..299 && hmBody.isNotEmpty()) {
            try {
                val json = JSONObject(hmBody)
                totalIncidents = json.optInt("total_incidents", totalIncidents)
                centerLat = json.optDouble("center_lat", centerLat)
                centerLon = json.optDouble("center_lon", centerLon)

                val pointsArr = json.optJSONArray("weighted_points") ?: JSONArray()
                for (i in 0 until pointsArr.length()) {
                    val p = pointsArr.getJSONObject(i)
                    pointsList.add(
                        HeatmapPoint(
                            lat = p.optDouble("lat", centerLat),
                            lon = p.optDouble("lon", centerLon),
                            weight = p.optDouble("weight", 0.8),
                            locationName = p.optString("location_name", "Risk Point")
                        )
                    )
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing heatmap: ${e.message}")
            }
        }

        val blackspotList = mutableListOf<BlackspotZone>()
        if (bsCode in 200..299 && bsBody.isNotEmpty()) {
            try {
                val json = JSONObject(bsBody)
                val bsArr = json.optJSONArray("blackspots") ?: JSONArray()
                for (i in 0 until bsArr.length()) {
                    val b = bsArr.getJSONObject(i)
                    blackspotList.add(
                        BlackspotZone(
                            id = b.optString("id", "BS_$i"),
                            name = b.optString("name", "Blackspot Zone"),
                            lat = b.optDouble("lat", 23.0),
                            lon = b.optDouble("lon", 72.0),
                            radiusM = b.optDouble("radius_m", 200.0),
                            color = "#9D0208",
                            historicalCrashes = b.optInt("historical_crashes", 20),
                            fatalities = b.optInt("fatalities", 3),
                            speedLimitKmh = b.optInt("speed_limit_kmh", 40)
                        )
                    )
                }
            } catch (e: Exception) {
                Log.w(TAG, "Error parsing blackspots: ${e.message}")
            }
        }

        heatmapOverview = HeatmapOverview(
            totalIncidents = totalIncidents,
            centerLat = centerLat,
            centerLon = centerLon,
            points = if (pointsList.isNotEmpty()) pointsList else heatmapOverview.points,
            blackspots = if (blackspotList.isNotEmpty()) blackspotList else heatmapOverview.blackspots
        )
        return heatmapOverview
    }

    // ========================================================
    // SYNCHRONOUS FALLBACK ACCESSORS
    // ========================================================

    fun register(name: String, email: String, pass: String): Boolean {
        currentUser = User("USR_${System.currentTimeMillis() % 100000}", name, email)
        userProfile = userProfile.copy(name = name, email = email, password = pass)
        return true
    }

    fun login(email: String, pass: String): Boolean {
        if (email.isNotEmpty() && pass.isNotEmpty()) {
            currentUser = User("USR_${System.currentTimeMillis() % 100000}", userProfile.name, email)
            return true
        }
        return false
    }

    fun getCurrentUser(): User? = currentUser

    fun getUserProfile(): UserProfile = userProfile

    fun updateUserProfile(updated: UserProfile) {
        userProfile = updated
    }

    fun getFrequentlyTraveledRoutes(): List<TravelRoute> = travelRoutes

    fun getHazardsForRoute(routeId: String): List<RouteHazard> {
        return travelRoutes.find { it.routeId == routeId }?.hazards ?: emptyList()
    }

    fun getRouteById(routeId: String): TravelRoute? {
        return travelRoutes.find { it.routeId == routeId }
    }

    fun getDriverScoreSummary(): DriverScoreSummary = driverScoreSummary

    fun getHeatmapOverview(): HeatmapOverview = heatmapOverview

    fun getAlertsForDestination(destination: String): List<NavigationAlert> {
        return listOf(
            NavigationAlert(
                alertId = "ALT-001",
                title = "Accident Prone Area Ahead",
                instruction = "High crash zone near Vaishno Devi circle. Reduce speed to 35 km/h.",
                severity = "HIGH",
                distanceAheadMeters = 350,
                category = "ACCIDENT_PRONE"
            ),
            NavigationAlert(
                alertId = "ALT-002",
                title = "Pothole Cluster 200m Ahead",
                instruction = "Multiple sharp surface craters on right lane. Shift to center lane cautiously.",
                severity = "HIGH",
                distanceAheadMeters = 200,
                category = "POTHOLE"
            ),
            NavigationAlert(
                alertId = "ALT-003",
                title = "Blind Curve & Speed Limit Warning",
                instruction = "Sharp blind hairpin curve 500m ahead. Speed limit restricted to 40 km/h.",
                severity = "MEDIUM",
                distanceAheadMeters = 500,
                category = "BLIND_CURVE"
            ),
            NavigationAlert(
                alertId = "ALT-004",
                title = "Speed Camera Geofence Active",
                instruction = "Automated telematics radar enforcement active. Maintain safe deceleration buffer.",
                severity = "LOW",
                distanceAheadMeters = 800,
                category = "SPEED_LIMIT"
            )
        )
    }
}
