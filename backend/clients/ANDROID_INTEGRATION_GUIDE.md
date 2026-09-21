# TECHNEXA 2026 — Android App Integration Guide
## High-Availability Live Telematics Streaming & Emergency Dispatch

### 🌐 Backend Base URLs
* **Local Wi-Fi Network**: `http://10.32.186.140:8000`
* **Public Cellular Tunnel**: `https://nasty-states-occur.loca.lt` *(Header: `Bypass-Tunnel-Reminder: true`)*

---

## 1. Streaming Phone GPS & Receiving Live Telematics

### `POST /api/gps`
The Android app streams device coordinates every 1–2 seconds.
**Crucial**: The backend now immediately returns the **enriched vehicle telematics payload** in the response! Your app does not need a second HTTP call.

#### Request Body:
```json
{
  "device_id": "VH001",
  "latitude": 23.033812,
  "longitude": 72.585045,
  "speed_kmh": 42.5,
  "heading_deg": 90.0,
  "accuracy_m": 4.5
}
```

#### Enriched Response Body (Ready for Android UI):
```json
{
  "status": "ok",
  "device_id": "VH001",
  "driver_score": 97.7,
  "tier": "PLATINUM SAFE",
  "badge_color": "success",
  "trend": "IMPROVING",
  "coaching_tip": "Maintain a 3-second following gap to avoid emergency braking shocks.",
  "pillars": {
    "smoothness": 100.0,
    "cornering": 100.0,
    "speed_compliance": 90.8,
    "vigilance": 100.0
  },
  "insurance_discount_pct": 25,
  "risk_score": 12.5,
  "risk_level": "LOW",
  "speed_limit_kmh": 50,
  "speed_status": "SAFE",
  "warnings": [],
  "nearest_blackspot": "Sarkhej-Gandhinagar Highway High-Speed Corridor",
  "distance_to_blackspot_m": 450.0,
  "is_inside_blackspot": false,
  "potholes_ahead": [
    {
      "id": "PH_001",
      "distance_m": 120,
      "severity": "SEVERE",
      "address": "SG Highway Service Road (Opp. Iscon)"
    }
  ],
  "emergency_alert": {
    "has_active_countdown": false,
    "remaining_sec": 0.0
  },
  "ui_cards": [
    {
      "card_type": "DRIVER_SCORECARD",
      "score": 97.7,
      "tier": "PLATINUM SAFE",
      "insurance_discount": "25% Off"
    },
    {
      "card_type": "SPEED_HUD",
      "speed_kmh": 42.5,
      "speed_limit_kmh": 50,
      "speed_status": "SAFE"
    }
  ]
}
```

---

## 2. Dedicated Android Dashboard Snapshot

### `GET /api/android/dashboard?device_id=VH001`
Use this endpoint when opening the app or refreshing the driver home screen. Returns pre-structured cards ready for RecyclerView or Jetpack Compose.

```kotlin
data class AndroidDashboardResponse(
    val header: HeaderData,
    val scorecard: ScorecardData,
    val speed_hud: SpeedHudData,
    val hazard_radar: HazardRadarData,
    val emergency: EmergencyData,
    val nearest_trauma_center: HospitalData
)

data class ScorecardData(
    val composite_score: Float,
    val tier: String,
    val badge_color: String,
    val trend: String,
    val coaching_tip: String,
    val insurance_discount_pct: Int,
    val pillars: Map<String, Float> // "smoothness", "cornering", "speed_compliance", "vigilance"
)
```

---

## 3. Real-Time Server-Sent Events (SSE) Push Stream

### `GET /api/stream/telemetry?device_id=VH001`
Instead of polling in a loop, your Android app can maintain a lightweight SSE connection using OkHttp. The backend pushes live telematics every second and instantly when incidents occur.

```kotlin
import okhttp3.*
import okhttp3.sse.*

val request = Request.Builder()
    .url("http://10.32.186.140:8000/api/stream/telemetry?device_id=VH001")
    .header("Accept", "text/event-stream")
    .header("Bypass-Tunnel-Reminder", "true")
    .build()

val client = OkHttpClient.Builder().build()
val factory = EventSources.createFactory(client)

factory.newEventSource(request, object : EventSourceListener() {
    override fun onEvent(eventSource: EventSource, id: String?, type: String?, data: String) {
        // Pushed JSON containing live score, 4 pillars, speed vs limit, and hazard alerts!
        // Run on main thread to update Compose UI
    }
})
```

---

## 4. Dead Man's Protocol: 1-Tap False Alarm Cancel

When the rider has a low-speed tip-over, kickstand drop, or false alarm, display a large prominent green button: **"I AM OK — CANCEL DISPATCH"**.

* **Endpoint**: `POST http://10.32.186.140:8000/api/emergency/cancel`
* **Response**: `{"status": "cancelled", "reason": "..."}`

---

## 5. Emergency SMS Dispatcher Integration

### 1. Android Manifest Permissions (`AndroidManifest.xml`)
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />
<uses-permission android:name="android.permission.SEND_SMS" />
```

### 2. Poll for Confirmed Crash Alerts (When 20s Countdown Expires)
* **Endpoint**: `GET http://10.32.186.140:8000/api/emergency/latest_pending`
* If `has_pending == true`, the rider remained motionless for 20 seconds. Send SMS using native `SmsManager`:

```kotlin
import android.telephony.SmsManager

fun dispatchEmergencySms(hospitalNumber: String, relativeNumber: String, messageText: String, alertId: String) {
    val smsManager = SmsManager.getDefault()
    val parts = smsManager.divideMessage(messageText)
    
    // Dispatch to Trauma Center & Family
    smsManager.sendMultipartTextMessage(hospitalNumber, null, parts, null, null)
    smsManager.sendMultipartTextMessage(relativeNumber, null, parts, null, null)

    // Acknowledge dispatch to backend
    acknowledgeAlert(alertId)
}
```

### 3. Acknowledge Alert
* **Endpoint**: `POST http://10.32.186.140:8000/api/emergency/acknowledge/{alert_id}`

---

## 6. Displaying the Heatmap & Blackspots in Android Studio

### API Endpoint: `GET /api/risk/heatmap`
Returns pre-processed data ready for Google Maps SDK and MapLibre:
* `weighted_points`: List of `{lat, lon, weight}` for `HeatmapTileProvider`
* `blackspot_zones`: List of `{id, name, lat, lon, radius_m, color, historical_crashes, fatalities, speed_limit_kmh}`
* `pothole_hazards`: List of crowdsourced potholes with `{lat, lon, severity, hit_count, address}`
* `geojson`: Standard GeoJSON FeatureCollection

### 1. Add Google Maps Utils to `build.gradle.kts` (Module: app)
```kotlin
dependencies {
    implementation("com.google.android.gms:play-services-maps:18.2.0")
    implementation("com.google.maps.android:android-maps-utils:3.8.0")
}
```

### 2. Render Thermal Heatmap on GoogleMap (Kotlin)
```kotlin
import com.google.android.gms.maps.GoogleMap
import com.google.android.gms.maps.model.LatLng
import com.google.android.gms.maps.model.TileOverlayOptions
import com.google.maps.android.heatmaps.HeatmapTileProvider
import com.google.maps.android.heatmaps.WeightedLatLng

fun renderHeatmap(googleMap: GoogleMap, weightedPoints: List<HeatmapPoint>) {
    // 1. Convert to Google Maps WeightedLatLng
    val dataList = weightedPoints.map { pt ->
        WeightedLatLng(LatLng(pt.lat, pt.lon), pt.weight)
    }

    if (dataList.isNotEmpty()) {
        // 2. Build High-Visibility Heatmap Tile Provider
        val provider = HeatmapTileProvider.Builder()
            .weightedData(dataList)
            .radius(45) // Pixels
            .opacity(0.7)
            .build()

        // 3. Add to Google Map
        googleMap.addTileOverlay(TileOverlayOptions().tileProvider(provider))
    }
}
```

### 3. Render Blackspot Danger Circles & Hotspot Markers
```kotlin
import android.graphics.Color
import com.google.android.gms.maps.model.CircleOptions
import com.google.android.gms.maps.model.MarkerOptions

fun renderBlackspotZones(googleMap: GoogleMap, zones: List<BlackspotZone>) {
    for (zone in zones) {
        val pos = LatLng(zone.lat, zone.lon)

        // 1. Semi-transparent Red Danger Zone Circle
        googleMap.addCircle(
            CircleOptions()
                .center(pos)
                .radius(zone.radius_m.toDouble())
                .strokeColor(Color.parseColor(zone.color ?: "#EF4444"))
                .fillColor(Color.argb(55, 239, 68, 68)) // ~22% opacity red fill
                .strokeWidth(3f)
        )

        // 2. Incident Pin with Crash Statistics
        googleMap.addMarker(
            MarkerOptions()
                .position(pos)
                .title("🔥 ${zone.name}")
                .snippet("Crashes: ${zone.historical_crashes} (${zone.fatalities} Fatalities) | Limit: ${zone.speed_limit_kmh} km/h")
        )
    }
}
```
