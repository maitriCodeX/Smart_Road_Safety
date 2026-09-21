# 🚀 Smart Road Safety Android UI Integration - Complete API Cheatsheet

### 🌐 Base URLs
* **Public Tunnel (Remote/Mobile Data)**: `https://nasty-falcon-37.loca.lt`
  * ⚠️ **Required Header**: `Bypass-Tunnel-Reminder: true`
* **Local LAN (Same Wi-Fi / Hotspot)**: `http://10.32.186.140:8000`
  * No extra headers required.

---

## 1. Authentication & Onboarding
Used for Login and Registration screens.

### `POST /api/auth/register`
* **Purpose**: Register a new user account.
* **Request Body**:
```json
{
  "name": "Rahul Sharma",
  "email": "rahul.sharma@example.com",
  "password": "SecurePass@2026",
  "confirm_password": "SecurePass@2026"
}
```
* **Response Body (`200 OK`)**:
```json
{
  "success": true,
  "message": "User registered successfully",
  "token": "jwt_token_USR_98241.1789999999.technexa_sig",
  "user": {
    "user_id": "USR_98241",
    "name": "Rahul Sharma",
    "email": "rahul.sharma@example.com"
  }
}
```

### `POST /api/auth/login`
* **Purpose**: Login existing user. *(Auto-provisions for hackathon convenience)*.
* **Request Body**:
```json
{
  "email": "rahul.sharma@example.com",
  "password": "SecurePass@2026"
}
```
* **Response Body (`200 OK`)**:
```json
{
  "success": true,
  "message": "Authentication successful",
  "token": "jwt_token_USR_98241.signature",
  "user": {
    "user_id": "USR_98241",
    "name": "Rahul Sharma",
    "email": "rahul.sharma@example.com"
  }
}
```

---

## 2. User Profile & Emergency Contact
Used for Profile Screen, Vehicle Details, and setting the Dead Man's Switch emergency contact.

### `GET /api/user/profile`
* **Purpose**: Fetch logged-in user profile and emergency contact.
* **Response Body (`200 OK`)**:
```json
{
  "user_id": "USR_98241",
  "name": "Rahul Sharma",
  "profile_picture_url": "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&w=400&q=80",
  "email": "rahul.sharma@example.com",
  "phone_number": "+91 98765 43210",
  "relative_phone_number": "+91 91234 56789",
  "age": 24,
  "blood_group": "B+",
  "car_plate_number": "GJ-01-AB-1234"
}
```

### `POST /api/user/profile` (or `PUT /api/user/profile`)
* **Purpose**: Update profile information. Updating `relative_phone_number` automatically updates the 20-second Dead Man's Switch SOS SMS dispatch number.
* **Request Body**:
```json
{
  "profile_picture_base64": null,
  "email": "rahul.sharma@example.com",
  "password": "UpdatedSecurePass@2026",
  "phone_number": "+91 98765 43210",
  "relative_phone_number": "+91 91234 56789",
  "age": 24,
  "blood_group": "B+",
  "car_plate_number": "GJ-01-AB-1234"
}
```
* **Response Body (`200 OK`)**: Returns updated profile JSON.

---

## 3. Ride Start & Real-Time Navigation Alerts
Used for the Navigation HUD and turn-by-turn road hazard cards.

### `POST /api/ride/start` (or `POST /api/navigation/start`)
* **Purpose**: Initialize a trip with destination and origin coordinates; returns ETA and hazard alerts ahead.
* **Request Body**:
```json
{
  "destination": "Mehsana Highway Bypass",
  "current_lat": 23.2156,
  "current_lon": 72.6369
}
```
* **Response Body (`200 OK`)**:
```json
{
  "destination": "Mehsana Highway Bypass",
  "origin": "Infocity, Gandhinagar",
  "distance_km": 54.2,
  "estimated_time_mins": 58,
  "alerts": [
    {
      "alert_id": "ALT-001",
      "title": "Accident Prone Area Ahead",
      "instruction": "High crash zone near Vaishno Devi circle. Reduce speed to 35 km/h.",
      "severity": "HIGH",
      "distance_ahead_m": 350,
      "category": "ACCIDENT_PRONE"
    },
    {
      "alert_id": "ALT-002",
      "title": "Road Defect: Deep Pothole Cluster",
      "instruction": "Severe pothole cluster in middle lane 50m ahead. Shift left safely.",
      "severity": "HIGH",
      "distance_ahead_m": 50,
      "category": "POTHOLE"
    },
    {
      "alert_id": "ALT-003",
      "title": "Sharp Blind S-Curve",
      "instruction": "Approaching unbanked curve near Kalol. Recommended limit 40 km/h.",
      "severity": "MEDIUM",
      "distance_ahead_m": 800,
      "category": "BLIND_CURVE"
    },
    {
      "alert_id": "ALT-004",
      "title": "Regulatory Speed Limit Enforcement",
      "instruction": "Entering NH-48 commercial corridor. Speed limit enforced at 60 km/h.",
      "severity": "LOW",
      "distance_ahead_m": 1200,
      "category": "SPEED_LIMIT"
    }
  ]
}
```

### `GET /api/navigation/alerts`
* **Purpose**: Fetch ongoing real-time navigation alerts during the active ride.
* **Response Body (`200 OK`)**: Returns `NavigationAlertsResponse` JSON.

---

## 4. Frequent Routes & Route Hazards Breakdown
Used for Frequent Routes list and Route Details Screen with hazard lists.

### `GET /api/hazards/frequent-routes`
* **Purpose**: Returns list of routes frequently traveled by the user.
* **Response Body (`200 OK`)**:
```json
[
  {
    "route_id": "ROUTE_GNR_MEH_01",
    "title": "Gandhinagar to Mehsana",
    "origin": "Gandhinagar CH Road",
    "destination": "Mehsana Highway Circle",
    "trip_count": 28,
    "total_distance_km": 68.5,
    "total_hazards_count": 6
  },
  {
    "route_id": "ROUTE_AHM_GNR_02",
    "title": "Ahmedabad to Gandhinagar",
    "origin": "Iskcon Crossroad, SG Highway",
    "destination": "Infocity, Gandhinagar",
    "trip_count": 45,
    "total_distance_km": 26.3,
    "total_hazards_count": 4
  },
  {
    "route_id": "ROUTE_SARKHEJ_03",
    "title": "Sarkhej to Sanand Industrial Hub",
    "origin": "Sarkhej Ujala Circle",
    "destination": "Sanand GIDC Auto Cluster",
    "trip_count": 14,
    "total_distance_km": 32.0,
    "total_hazards_count": 5
  }
]
```

### `GET /api/hazards/route-detail?route_id=ROUTE_GNR_MEH_01`
*(Also accessible via `GET /api/hazards/routes/{route_id}`)*
* **Purpose**: Returns granular hazards (potholes, blackspots, curves, waterlogging) for the selected route.
* **Response Body (`200 OK`)**:
```json
{
  "route_id": "ROUTE_GNR_MEH_01",
  "route_title": "Gandhinagar to Mehsana",
  "hazards": [
    {
      "hazard_id": "HAZ_001",
      "hazard_type": "POTHOLE",
      "title": "Severe Pothole Cluster",
      "nearby_location": "Near: 50m past S-DMart, Kudasan Crossroad",
      "description": "Multiple deep surface potholes across middle and right lanes detected by IMU jerk sensor",
      "severity": "CRITICAL",
      "lat": 23.1894,
      "lon": 72.6281
    },
    {
      "hazard_id": "HAZ_002",
      "hazard_type": "ACCIDENT_BLACKSPOT",
      "title": "Chhatral GIDC Highway Junction Blackspot",
      "nearby_location": "Near: Chhatral Overbridge Exit",
      "description": "High fatality intersection: heavy industrial container trucks merging without turn signals",
      "severity": "CRITICAL",
      "lat": 23.3325,
      "lon": 72.4389
    },
    {
      "hazard_id": "HAZ_003",
      "hazard_type": "BLIND_CURVE",
      "title": "Sharp S-Curve with Obstructed Visibility",
      "nearby_location": "Near: Kalol Toll Plaza bypass",
      "description": "High-speed blind curve; recommended entry speed 40 km/h",
      "severity": "MODERATE",
      "lat": 23.251,
      "lon": 72.498
    },
    {
      "hazard_id": "HAZ_004",
      "hazard_type": "WATER_LOGGING",
      "title": "Monsoon Waterlogged Underpass",
      "nearby_location": "Near: Nandasan Railway Underpass",
      "description": "Standing water up to 25cm during rains causing hydroplaning risk",
      "severity": "MODERATE",
      "lat": 23.412,
      "lon": 72.415
    },
    {
      "hazard_id": "HAZ_005",
      "hazard_type": "POTHOLE",
      "title": "Bridge Expansion Joint Trench",
      "nearby_location": "Near: Mehsana Southern Bypass Bridge",
      "description": "Abrupt 7cm asphalt drop causing harsh vertical chassis shock",
      "severity": "CRITICAL",
      "lat": 23.572,
      "lon": 72.378
    },
    {
      "hazard_id": "HAZ_006",
      "hazard_type": "ACCIDENT_BLACKSPOT",
      "title": "Civil Hospital Mehsana Ambulance Corridor",
      "nearby_location": "Near: Radhanpur Road Crossroad",
      "description": "Frequent emergency vehicle crossing with uncontrolled median gap",
      "severity": "LOW",
      "lat": 23.59,
      "lon": 72.39
    }
  ]
}
```

---

## 5. Driver Safety Score & Fine Tickets
Used for Driver Score Dashboard, 4 Pillar meters, and Traffic E-Challans.

### `GET /api/driver/score`
* **Purpose**: Fetches 4-pillar telematics score, actuarial tier, and traffic fine tickets.
* **Response Body (`200 OK`)**:
```json
{
  "overall_score": 100,
  "actuarial_tier": "Platinum Safe",
  "insurance_discount_pct": 25,
  "trend": "STABLE",
  "pillars": {
    "smoothness_pct": 100,
    "cornering_pct": 100,
    "speed_compliance_pct": 100,
    "vigilance_pct": 100
  },
  "fine_tickets": [
    {
      "ticket_id": "TCK-2026-901",
      "reason": "Overspeeding > 80 km/h at SG Highway",
      "date": "18 Sep 2026, 04:15 PM",
      "amount": "₹1,000",
      "amount_numeric": 1000.0,
      "status": "UNPAID",
      "location": "SG Highway Flyover near Vaishno Devi"
    },
    {
      "ticket_id": "TCK-2026-784",
      "reason": "Harsh Lane Change Without Indicator",
      "date": "12 Sep 2026, 09:30 AM",
      "amount": "₹500",
      "amount_numeric": 500.0,
      "status": "PAID",
      "location": "Kudasan Crossroad, Gandhinagar"
    }
  ]
}
```

---

## 6. High-Density Heatmap & Danger Zones
Used for Google Maps / MapLibre overlays (`HeatmapTileProvider` and `CircleOptions`).

### `GET /api/heatmap`
* **Purpose**: Returns 132 Gaussian-weighted heat points and danger zone circle definitions.
* **Response Body (`200 OK`)**:
```json
{
  "total_incidents": 132,
  "center_lat": 23.1124,
  "center_lon": 72.5489,
  "weighted_points": [
    {
      "lat": 23.0298,
      "lon": 72.5074,
      "weight": 0.95,
      "location_name": "Iskcon Crossroad Blackspot"
    }
  ],
  "blackspot_zones": [
    {
      "id": "BS-01",
      "name": "Iskcon Crossroad Blackspot",
      "lat": 23.0298,
      "lon": 72.5074,
      "radius_m": 250.0,
      "color": "#9D0208",
      "historical_crashes": 42,
      "fatalities": 7,
      "speed_limit_kmh": 35
    }
  ]
}
```

---

## 7. Real-Time Telematics & Mobile Sensor Ingest

### `POST /api/gps`
* **Purpose**: Stream live vehicle GPS from phone; receives real-time score feedback, ahead potholes, and UI cards.
* **Request Body**:
```json
{
  "device_id": "VH001",
  "latitude": 23.0225,
  "longitude": 72.5714,
  "speed": 45.0,
  "heading_deg": 180.0
}
```
* **Response Body (`200 OK`)**:
```json
{
  "status": "updated",
  "device_id": "VH001",
  "driver_score": 100.0,
  "tier": "PLATINUM SAFE",
  "pillars": {
    "smoothness": 100.0,
    "cornering": 100.0,
    "speed_compliance": 100.0,
    "vigilance": 100.0
  },
  "speed_hud": {
    "current_speed_kmh": 45.0,
    "speed_limit_kmh": 60,
    "speed_status": "SAFE"
  },
  "ui_cards": [
    {
      "type": "DRIVER_SCORE_CARD",
      "title": "Driver Safety Index",
      "score": 100.0,
      "tier": "PLATINUM SAFE",
      "coaching_tip": "Maintain a 3-second following gap to avoid emergency braking shocks."
    }
  ]
}
```

### `GET /api/android/dashboard`
* **Purpose**: Single high-availability call for native RecyclerView or Jetpack Compose dashboard snapshot.

### `GET /api/stream/telemetry`
* **Purpose**: Server-Sent Events (SSE) stream (`text/event-stream`). Emits 1-second continuous live telemetry packets.

---

## 8. Emergency Crash & Dead Man's Switch (20-Second Window)

### `GET /api/emergency/latest_pending`
* **Purpose**: Poll or check if a crash countdown is actively running.
* **Response Body (`200 OK`)**:
```json
{
  "has_pending": true,
  "countdown": {
    "has_active_countdown": true,
    "alert_id": "ALT_1789",
    "remaining_sec": 14.2,
    "status": "COUNTDOWN_VERIFYING"
  }
}
```

### `POST /api/emergency/cancel`
* **Purpose**: "I AM SAFE / FALSE ALARM" button. Immediately aborts the 20-second countdown and prevents SOS SMS dispatch.
* **Response Body (`200 OK`)**:
```json
{
  "status": "cancelled",
  "reason": "Rider pressed 'I am OK (False Alarm)'"
}
```
