import time
import math
import requests
import sys
import os
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from typing import Optional, List
import json
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel

# Add both current directory and parent directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
for p in [current_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

import threading
try:
    from ml.risk_engine import risk_engine
    from ml.safety_scorer import driver_scorer
    from ml.pothole_tracker import pothole_tracker
    from ml.blackspots_data import get_all_blackspots
    from ml.blackbox_manager import blackbox_mgr
except ImportError:
    from backend.ml.risk_engine import risk_engine
    from backend.ml.safety_scorer import driver_scorer
    from backend.ml.pothole_tracker import pothole_tracker
    from backend.ml.blackspots_data import get_all_blackspots
    from backend.ml.blackbox_manager import blackbox_mgr

app = FastAPI(title="TechNexa 2026 - Smart Road Safety Backend")

# Enable CORS for phone gateways, web dashboards, or teammate frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from android_contract import router as android_contract_router
except ImportError:
    from backend.android_contract import router as android_contract_router
app.include_router(android_contract_router)

# ============================================================================
# DATA MODELS
# ============================================================================
class VehicleEvent(BaseModel):
    device_id: str = "VH001"
    event: str
    severity: float
    peak_value: float
    duration_ms: Optional[int] = 0
    timestamp_ms: Optional[int] = 0

class PartnerConfig(BaseModel):
    url: str

class GPSLocation(BaseModel):
    device_id: Optional[str] = "VH001"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    lng: Optional[float] = None
    speed_kmh: Optional[float] = 0.0
    speed: Optional[float] = 0.0
    heading_deg: Optional[float] = 0.0
    accuracy_m: Optional[float] = 5.0
    timestamp: Optional[float] = None

class EmergencyAlert(BaseModel):
    alert_id: str
    device_id: str
    timestamp: float
    severity: str
    impact_peak_ms2: float
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    nearest_hospital: dict
    relative_contact: dict
    prepared_sms_text: str
    status: str = "PENDING_DISPATCH" # PENDING_DISPATCH, SENT, ACKNOWLEDGED

# ============================================================================
# IN-MEMORY STATE & REGISTRATION
# ============================================================================
latest_gps = {
    "VH001": {
        "latitude": 23.0225,
        "longitude": 72.5714,
        "speed_kmh": 0.0,
        "heading_deg": 0.0,
        "accuracy_m": 5.0,
        "last_updated": 0,
        "is_live": False,
        "source": "Waiting for live Android GPS stream"
    }
}

events_log = []
emergency_alerts = []

# Pre-seeded emergency hospital registry (Pilot area)
HOSPITALS = [
    {
        "name": "Civil Hospital Mehsana",
        "lat": 23.5900,
        "lon": 72.3900,
        "phone": "+91 2762 252 000",
        "trauma_level": "Level 1"
    },
    {
        "name": "Apollo City Emergency Center",
        "lat": 23.0305,
        "lon": 72.5650,
        "phone": "+91 79 2656 1234",
        "trauma_level": "Level 1"
    },
    {
        "name": "Civil Metro Trauma Hospital",
        "lat": 23.0520,
        "lon": 72.5950,
        "phone": "+91 79 2268 0000",
        "trauma_level": "Level 1"
    },
    {
        "name": "Shalby Multispecialty Care",
        "lat": 23.0140,
        "lon": 72.5080,
        "phone": "+91 79 4020 3000",
        "trauma_level": "Level 2"
    }
]

DEFAULT_RELATIVE = {
    "name": "Primary Emergency Contact",
    "relation": "Family / Next of Kin",
    "phone": "+91 98765 43210"
}

# Teammate's messaging backend URL
messaging_config = {
    "partner_emergency_url": "http://10.32.186.215:8080/send-sms",
    "default_place": "Mehsana, Gujarat"
}

_geo_cache = {}

def get_place_name(lat, lon):
    if lat is None or lon is None:
        return messaging_config["default_place"]
    cache_key = (round(lat, 3), round(lon, 3))
    if cache_key in _geo_cache:
        return _geo_cache[cache_key]

    # Quick regional heuristics (zero latency)
    if 23.4 < lat < 23.8 and 72.1 < lon < 72.6:
        name = "Mehsana, Gujarat"
        _geo_cache[cache_key] = name
        return name
    if 22.9 < lat < 23.3 and 72.4 < lon < 72.7:
        name = "SG Highway, Ahmedabad, Gujarat"
        _geo_cache[cache_key] = name
        return name

    # Reverse geocode via OpenStreetMap Nominatim with 1.5s timeout
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=16&addressdetails=1"
        resp = requests.get(url, headers={"User-Agent": "TechNexaRoadSafety/1.0"}, timeout=1.5)
        if resp.status_code == 200:
            data = resp.json()
            addr = data.get("address", {})
            road = addr.get("road") or addr.get("suburb") or addr.get("neighbourhood")
            city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county")
            state = addr.get("state")
            parts = [p for p in [road, city, state] if p]
            if parts:
                resolved = ", ".join(parts)
                _geo_cache[cache_key] = resolved
                return resolved
    except Exception:
        pass

    fallback = f"Location ({lat:.4f}, {lon:.4f})"
    _geo_cache[cache_key] = fallback
    return fallback

def forward_to_partner_messaging(hospital: dict, relative: dict, date_time: str, place: str,
                                lat: float = None, lon: float = None, maps_link: str = None,
                                speed: float = 0.0, peak_value: float = 0.0):
    target_url = messaging_config.get("partner_emergency_url")
    if not target_url:
        return

    # Message formatted as teammate requested, plus live Google Maps link:
    loc_part = f" Live Location: {maps_link} ." if maps_link else ""
    msg = f"Accident happened at {place} on {date_time}.{loc_part} Emergency message sent to {hospital['name']}."

    # Send SMS payload to Partner Android Gateway
    payload_rel = {
        "phone": relative.get("phone", "+919876543210"),
        "message": msg,
        "date_time": date_time,
        "place": place,
        "hospital": hospital["name"],
        "hospital_phone": hospital.get("phone", ""),
        "latitude": lat,
        "longitude": lon,
        "google_maps_url": maps_link,
        "speed_kmh": speed,
        "impact_peak_ms2": peak_value
    }

    try:
        res = requests.post(target_url, json=payload_rel, timeout=5)
        print(f"\n[PARTNER SMS DISPATCH] Relative SMS -> Status: {res.status_code} | {res.text}")
    except Exception as e:
        print(f"\n[PARTNER SMS DISPATCH] Error reaching {target_url}: {e}")

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def find_nearest_hospital(lat, lon):
    if lat is None or lon is None:
        return HOSPITALS[0]
    best_hosp = HOSPITALS[0]
    min_dist = float('inf')
    for h in HOSPITALS:
        dist = haversine_km(lat, lon, h["lat"], h["lon"])
        if dist < min_dist:
            min_dist = dist
            best_hosp = {**h, "distance_km": round(dist, 2)}
    return best_hosp

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.post("/api/events")
def ingest_event(evt: VehicleEvent):
    """
    Called directly by the ESP32 over Wi-Fi when an event is detected.
    """
    now = time.time()
    gps_data = latest_gps.get(evt.device_id, {})
    lat = gps_data.get("latitude")
    lon = gps_data.get("longitude")
    speed = gps_data.get("speed_kmh", 0.0)

    record = {
        "id": len(events_log) + 1,
        "device_id": evt.device_id,
        "event": evt.event,
        "severity": evt.severity,
        "peak_value": evt.peak_value,
        "duration_ms": evt.duration_ms,
        "timestamp_ms": evt.timestamp_ms,
        "received_at": now,
        "latitude": lat,
        "longitude": lon,
        "speed_kmh": speed
    }
    events_log.insert(0, record)
    if len(events_log) > 200:
        events_log.pop()

    print(f"\n[BACKEND] Ingested {evt.event} from {evt.device_id} | Peak: {evt.peak_value} | Severity: {evt.severity} | GPS: ({lat}, {lon})")

    # Record IMU telemetry into Blackbox buffer
    blackbox_mgr.record_telemetry(
        speed_kmh=speed, lat=lat, lon=lon,
        g_force=evt.peak_value / 9.81,
        tilt_deg=evt.peak_value if "ROLLOVER" in evt.event else 0.0
    )

    # 1. Autonomous Road Hazard Mapping (Civic ITS)
    if evt.event == "POTHOLE":
        addr = get_place_name(lat, lon)
        pothole_tracker.register_pothole(lat, lon, peak_jerk=evt.peak_value, peak_g=evt.severity * 2.5, address=addr)
        driver_scorer.register_event("POTHOLE_IMPACT", severity=evt.severity, details=f"Peak jerk {evt.peak_value:.1f} m/s3")

    # 2. Driver Safety Behavior Profiling
    elif evt.event in ["HARSH_BRAKING", "AGGRESSIVE_CORNERING", "HARSH_ACCELERATION"]:
        driver_scorer.register_event(evt.event, severity=evt.severity, details=f"Peak {evt.peak_value:.1f} m/s2")

    # If event is a COLLISION, trigger Dead Man's Protocol & Blackbox freeze
    if evt.event in ["COLLISION", "ROLLOVER_TILT"]:
        hosp = find_nearest_hospital(lat, lon)
        alert_id = f"ALERT-{int(now * 1000)}"
        
        date_str = time.strftime('%Y-%m-%d', time.localtime(now))
        time_str = time.strftime('%H:%M:%S', time.localtime(now))
        maps_link = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else "https://maps.google.com"
        sms_text = (
            f"EMERGENCY ALERT: Severe vehicle crash detected for {evt.device_id}!\n"
            f"Date: {date_str} | Time: {time_str}\n"
            f"Impact: {evt.peak_value:.1f} m/s2 | Speed: {speed:.1f} km/h\n"
            f"Location: {maps_link}\n"
            f"Nearest Trauma: {hosp['name']} ({hosp.get('distance_km', 'N/A')} km)\n"
            f"Hospital Phone: {hosp['phone']}"
        )

        alert_obj = {
            "alert_id": alert_id,
            "device_id": evt.device_id,
            "event": evt.event,
            "timestamp": now,
            "date": date_str,
            "time": time_str,
            "severity": "CRITICAL" if evt.severity > 0.75 else "HIGH",
            "impact_peak_ms2": evt.peak_value,
            "speed_kmh": speed,
            "latitude": lat,
            "longitude": lon,
            "google_maps_url": maps_link,
            "hospital_name": hosp["name"],
            "hospital_phone": hosp["phone"],
            "hospital_distance_km": hosp.get("distance_km", 0.0),
            "relative_name": DEFAULT_RELATIVE["name"],
            "relative_phone": DEFAULT_RELATIVE["phone"],
            "sms_body": sms_text,
            "status": "COUNTDOWN_VERIFYING",
            "nearest_hospital": hosp,
            "relative_contact": DEFAULT_RELATIVE,
            "prepared_sms_text": sms_text
        }

        # Freeze Rolling Blackbox & Generate Forensic Reconstruction Packet
        bb_report = blackbox_mgr.trigger_crash_event(alert_id, alert_obj, timeout_sec=20)
        alert_obj["blackbox"] = bb_report
        emergency_alerts.insert(0, alert_obj)
        print(f"\n[DEAD MAN'S PROTOCOL] Triggered 20s Incapacitation Countdown for {alert_id} | Blackbox {bb_report['blackbox_id']} compiled")

        # Delayed Dispatch Worker: Only dispatches if NOT cancelled within 20s
        formatted_dt = time.strftime("%d %B %Y, %I:%M %p", time.localtime(now))
        place_str = get_place_name(lat, lon)

        def _delayed_dispatch_worker(a_id, h, rel, dt, pl, lt, ln, ml, sp, pk):
            time.sleep(20)
            eval_res = blackbox_mgr.active_crash_evaluations.get(a_id, {})
            if eval_res.get("status") in ["COUNTDOWN_VERIFYING", "DISPATCH_LOCKED"]:
                eval_res["status"] = "DISPATCH_LOCKED"
                print(f"[DEAD MAN'S PROTOCOL] 20s Countdown Expired (Incapacitated Rider Confirmed). Dispatching SMS for {a_id}!")
                forward_to_partner_messaging(h, rel, dt, pl, lt, ln, ml, sp, pk)
                for a in emergency_alerts:
                    if a["alert_id"] == a_id:
                        a["status"] = "DISPATCH_CONFIRMED"
            else:
                print(f"[DEAD MAN'S PROTOCOL] SMS Dispatch ABORTED for {a_id}! Reason: {eval_res.get('cancel_reason')}")

        t = threading.Thread(target=_delayed_dispatch_worker, args=(
            alert_id, hosp, DEFAULT_RELATIVE, formatted_dt, place_str, lat, lon, maps_link, speed, evt.peak_value
        ), daemon=True)
        t.start()

    return {"status": "success", "event_id": record["id"], "linked_gps": {"lat": lat, "lon": lon}}

@app.post("/api/gps")
def update_gps(loc: GPSLocation):
    """
    Called continuously by the Android phone app to stream vehicle GPS coordinates.
    """
    lat = loc.latitude if loc.latitude is not None else loc.lat
    lon = loc.longitude if loc.longitude is not None else (loc.lon if loc.lon is not None else loc.lng)
    speed = loc.speed_kmh if loc.speed_kmh is not None else (loc.speed if loc.speed is not None else 0.0)
    dev_id = loc.device_id or "VH001"

    if lat is None or lon is None:
        raise HTTPException(status_code=400, detail="Latitude and longitude coordinates are required")

    is_sim = (dev_id == "SIM_VEHICLE")
    entry = {
        "device_id": dev_id,
        "latitude": round(lat, 6),
        "longitude": round(lon, 6),
        "speed_kmh": round(speed, 1),
        "heading_deg": round(loc.heading_deg or 0.0, 1),
        "accuracy_m": round(loc.accuracy_m or 5.0, 1),
        "last_updated": time.time(),
        "is_live": not is_sim,
        "source": "Demonstration Simulator" if is_sim else "Android Phone Live GPS Stream"
    }

    latest_gps[dev_id] = entry
    if not is_sim:
        latest_gps["VH001"] = entry
        # Record telemetry into Blackbox buffer and check Dead Man's kinematic recovery
        blackbox_mgr.record_telemetry(speed_kmh=speed, lat=lat, lon=lon)
        risk_assessment = risk_engine.assess_risk(lat, lon, speed_kmh=speed)
        print(f"\n[ANDROID GPS RECEIVED] Lat: {lat:.6f}, Lon: {lon:.6f} | Speed: {speed:.1f} km/h (Live Device: {dev_id})")
    else:
        risk_assessment = risk_engine.assess_risk(lat, lon, speed_kmh=speed)
        print(f"\n[SIMULATION STEP] Lat: {lat:.6f}, Lon: {lon:.6f} | Speed: {speed:.1f} km/h (SIM_VEHICLE)")

    # Comprehensive 4-pillar telematics profile and countdown status
    score_profile = driver_scorer.get_profile()
    countdown_info = blackbox_mgr.get_evaluation_status()

    # Pre-formatted Android UI cards ready for RecyclerView / Jetpack Compose
    ui_cards = [
        {
            "card_type": "DRIVER_SCORECARD",
            "title": "Driver Safety Index",
            "score": score_profile["score"],
            "tier": score_profile["tier"],
            "badge_color": score_profile["badge_color"],
            "trend": score_profile["trend"],
            "coaching_tip": score_profile["tip"],
            "pillars": score_profile["pillars"],
            "insurance_discount": f"{score_profile['insurance']['discount_percent']}% Off"
        },
        {
            "card_type": "SPEED_HUD",
            "title": "Road Speed Telematics",
            "speed_kmh": round(speed, 1),
            "speed_limit_kmh": risk_assessment["speed_limit_kmh"],
            "speed_status": risk_assessment.get("speed_status", "SAFE"),
            "delta_overspeed_kmh": risk_assessment.get("delta_overspeed_kmh", 0.0)
        },
        {
            "card_type": "BLACKSPOT_RADAR",
            "title": "Geospatial Hazard Warning",
            "nearest_blackspot": risk_assessment.get("nearest_blackspot"),
            "distance_m": risk_assessment.get("distance_to_blackspot_m"),
            "is_inside": risk_assessment.get("is_inside_blackspot", False),
            "hazard_type": risk_assessment.get("blackspot_hazard", "None"),
            "risk_level": risk_assessment["risk_level"]
        },
        {
            "card_type": "ROAD_SURFACE_DEFECTS",
            "title": "Upcoming Potholes",
            "hazards": risk_assessment.get("potholes_ahead", [])
        }
    ]

    return {
        "status": "ok",
        "device_id": dev_id,
        "latitude": lat,
        "longitude": lon,
        "speed_kmh": speed,
        "google_maps_url": f"https://www.google.com/maps?q={lat},{lon}",
        "driver_score": score_profile["score"],
        "tier": score_profile["tier"],
        "badge_color": score_profile["badge_color"],
        "trend": score_profile["trend"],
        "coaching_tip": score_profile["tip"],
        "pillars": score_profile["pillars"],
        "insurance_discount_pct": score_profile["insurance"]["discount_percent"],
        "risk_score": risk_assessment["risk_score"],
        "risk_level": risk_assessment["risk_level"],
        "speed_limit_kmh": risk_assessment["speed_limit_kmh"],
        "speed_status": risk_assessment.get("speed_status", "SAFE"),
        "warnings": risk_assessment["warnings"],
        "nearest_blackspot": risk_assessment.get("nearest_blackspot"),
        "distance_to_blackspot_m": risk_assessment.get("distance_to_blackspot_m"),
        "is_inside_blackspot": risk_assessment.get("is_inside_blackspot", False),
        "potholes_ahead": risk_assessment.get("potholes_ahead", []),
        "emergency_alert": {
            "has_active_countdown": bool(countdown_info and countdown_info.get("has_active_countdown")),
            "remaining_sec": countdown_info.get("remaining_sec", 0.0) if countdown_info else 0.0
        },
        "ui_cards": ui_cards
    }

@app.get("/api/android/dashboard")
def get_android_dashboard(device_id: str = "VH001"):
    """
    High-availability snapshot endpoint optimized specifically for Android UI clients.
    Provides complete structured JSON for Driver Scorecard, Pillars, Gauges, and Hazard HUD.
    """
    gps = latest_gps.get(device_id) or latest_gps.get("VH001") or {}
    lat = gps.get("latitude")
    lon = gps.get("longitude")
    speed = gps.get("speed_kmh", 0.0)
    last_updated = gps.get("last_updated", 0)
    is_live = gps.get("is_live", False)

    now = time.time()
    ping_age_sec = round(now - last_updated, 1) if last_updated > 0 else 999.0
    conn_status = "STREAMING_LIVE" if (is_live and ping_age_sec < 10.0) else "DISCONNECTED"

    risk_info = risk_engine.assess_risk(lat, lon, speed_kmh=speed)
    score_info = driver_scorer.get_profile()
    countdown_info = blackbox_mgr.get_evaluation_status()
    hosp = find_nearest_hospital(lat, lon)

    return {
        "header": {
            "device_id": device_id,
            "connection_status": conn_status,
            "ping_age_sec": ping_age_sec,
            "latitude": lat,
            "longitude": lon,
            "speed_kmh": round(speed, 1),
            "timestamp": now
        },
        "scorecard": {
            "composite_score": score_info["score"],
            "tier": score_info["tier"],
            "profile": score_info["profile"],
            "badge_color": score_info["badge_color"],
            "trend": score_info["trend"],
            "coaching_tip": score_info["tip"],
            "description": score_info["description"],
            "insurance_discount_pct": score_info["insurance"]["discount_percent"],
            "insurance_status": score_info["insurance"]["status"],
            "pillars": score_info["pillars"],
            "event_counts": score_info["counts"]
        },
        "speed_hud": {
            "current_speed_kmh": round(speed, 1),
            "speed_limit_kmh": risk_info["speed_limit_kmh"],
            "speed_status": risk_info.get("speed_status", "SAFE"),
            "delta_overspeed_kmh": risk_info.get("delta_overspeed_kmh", 0.0)
        },
        "hazard_radar": {
            "risk_score": risk_info["risk_score"],
            "risk_level": risk_info["risk_level"],
            "badge_color": risk_info["badge_color"],
            "warnings": risk_info["warnings"],
            "nearest_blackspot": risk_info.get("nearest_blackspot"),
            "distance_to_blackspot_m": risk_info.get("distance_to_blackspot_m"),
            "is_inside_blackspot": risk_info.get("is_inside_blackspot", False),
            "potholes_ahead": risk_info.get("potholes_ahead", [])
        },
        "emergency": {
            "has_active_countdown": bool(countdown_info and countdown_info.get("has_active_countdown")),
            "remaining_sec": countdown_info.get("remaining_sec", 0.0) if countdown_info else 0.0,
            "status": countdown_info.get("status") if countdown_info else "NORMAL",
            "cancel_endpoint": "/api/emergency/cancel"
        },
        "nearest_trauma_center": hosp
    }

@app.get("/api/stream/telemetry")
async def stream_telemetry_events(device_id: str = "VH001"):
    """
    Server-Sent Events (SSE) Push Stream for Android App & Web Dashboards.
    Allows client to maintain a single HTTP connection and receive live telematics pushed continuously.
    """
    async def event_generator():
        while True:
            gps = latest_gps.get(device_id) or latest_gps.get("VH001") or {}
            lat = gps.get("latitude")
            lon = gps.get("longitude")
            speed = gps.get("speed_kmh", 0.0)

            risk_info = risk_engine.assess_risk(lat, lon, speed_kmh=speed)
            score_info = driver_scorer.get_profile()
            countdown_info = blackbox_mgr.get_evaluation_status()

            packet = {
                "timestamp": time.time(),
                "device_id": device_id,
                "gps": gps,
                "driver_score": score_info["score"],
                "tier": score_info["tier"],
                "trend": score_info["trend"],
                "pillars": score_info["pillars"],
                "coaching_tip": score_info["tip"],
                "insurance_discount_pct": score_info["insurance"]["discount_percent"],
                "risk_score": risk_info["risk_score"],
                "risk_level": risk_info["risk_level"],
                "speed_limit_kmh": risk_info["speed_limit_kmh"],
                "speed_status": risk_info.get("speed_status", "SAFE"),
                "warnings": risk_info["warnings"],
                "nearest_blackspot": risk_info.get("nearest_blackspot"),
                "distance_to_blackspot_m": risk_info.get("distance_to_blackspot_m"),
                "is_inside_blackspot": risk_info.get("is_inside_blackspot", False),
                "potholes_ahead": risk_info.get("potholes_ahead", []),
                "countdown": countdown_info
            }
            yield f"data: {json.dumps(packet)}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/events")
def get_events(limit: int = 50):
    """
    Returns latest vehicle events for dashboards or processing.
    """
    return {"count": len(events_log), "events": events_log[:limit]}

@app.get("/api/gps/latest")
def get_latest_gps(device_id: str = "VH001"):
    """
    Returns current location coordinates of the vehicle.
    """
    if device_id in latest_gps:
        return latest_gps[device_id]
    raise HTTPException(status_code=404, detail="Vehicle not found")

@app.get("/api/risk/current")
def get_current_risk(device_id: str = "VH001"):
    """
    Predictive Accident-Risk assessment for the vehicle.
    """
    gps = latest_gps.get(device_id) or latest_gps.get("VH001") or {}
    lat = gps.get("latitude")
    lon = gps.get("longitude")
    speed = gps.get("speed_kmh", 0.0)
    return risk_engine.assess_risk(lat, lon, speed_kmh=speed)

@app.get("/api/risk/heatmap")
def get_risk_heatmap():
    """
    Returns multi-format heatmap data for Leaflet Heat and Android Studio (Google Maps / MapLibre).
    Includes points, weighted_points, blackspot_zones, and GeoJSON.
    """
    return risk_engine.get_heatmap_data()

@app.get("/api/risk/blackspots")
def get_blackspots():
    """
    Returns list of all registered high-risk accident blackspots.
    """
    return {"count": len(risk_engine.blackspots), "blackspots": risk_engine.blackspots}

@app.get("/api/safety/score")
def get_driver_safety_score():
    """
    Returns Driver Safety Index (0-100), behavior profile, and telematics breakdown.
    """
    return driver_scorer.get_profile()

@app.get("/api/hazards/potholes")
def get_pothole_hazards():
    """
    Returns crowdsourced road hazards and municipal Road Quality Index (RQI).
    """
    return pothole_tracker.get_road_quality_index()

@app.get("/api/gps/all")
def get_all_gps():
    """
    Returns all tracked devices (live Android phone and any simulation vehicle).
    """
    return latest_gps

@app.post("/api/simulation/drive_step")
def simulate_drive_step(step: dict):
    """
    Simulates a vehicle moving along a highway route for live hackathon judge demonstrations.
    Uses SIM_VEHICLE so it NEVER overwrites the live Android phone stream.
    """
    lat = step.get("lat")
    lon = step.get("lon")
    speed = step.get("speed", 45.0)
    loc = GPSLocation(device_id="SIM_VEHICLE", latitude=lat, longitude=lon, speed_kmh=speed)
    return update_gps(loc)

@app.post("/api/emergency/cancel")
@app.post("/api/emergency/cancel/{alert_id}")
def cancel_emergency_alert(alert_id: Optional[str] = None):
    """
    Dead Man's Protocol: Allows rider or dashboard to cancel false alarm during 20s countdown.
    """
    if not alert_id:
        for a_id, ev in reversed(list(blackbox_mgr.active_crash_evaluations.items())):
            if ev["status"] == "COUNTDOWN_VERIFYING":
                alert_id = a_id
                break
    if not alert_id:
        return {"status": "no_active_countdown"}

    res = blackbox_mgr.cancel_alert(alert_id, reason="Rider pressed 'I am OK (False Alarm)'")
    for a in emergency_alerts:
        if a["alert_id"] == alert_id:
            a["status"] = "CANCELLED_FALSE_ALARM"
    return res

@app.get("/api/emergency/countdown")
def get_crash_countdown():
    """
    Returns active Dead Man's Protocol countdown timer and status.
    """
    status = blackbox_mgr.get_evaluation_status()
    if status:
        return {
            "has_active_countdown": True,
            "alert_id": status["alert_id"],
            "remaining_sec": status["remaining_sec"],
            "status": status["status"],
            "cancel_reason": status.get("cancel_reason"),
            "report": status.get("report")
        }
    return {"has_active_countdown": False}

@app.get("/api/emergency/blackbox/latest")
def get_latest_blackbox():
    """
    Returns latest compiled forensic crash reconstruction packet.
    """
    if blackbox_mgr.frozen_blackbox_reports:
        latest_id = list(blackbox_mgr.frozen_blackbox_reports.keys())[-1]
        return blackbox_mgr.frozen_blackbox_reports[latest_id]
    raise HTTPException(status_code=404, detail="No blackbox crash reports on file")

@app.get("/api/emergency/blackbox/{alert_id}")
def get_blackbox_report(alert_id: str):
    """
    Returns full forensic reconstruction packet for insurance / police investigation.
    """
    if alert_id in blackbox_mgr.frozen_blackbox_reports:
        return blackbox_mgr.frozen_blackbox_reports[alert_id]
    raise HTTPException(status_code=404, detail="Blackbox record not found")

@app.get("/api/emergency/alerts")
def get_emergency_alerts():
    """
    For the Android app to view all alerts.
    """
    return {"count": len(emergency_alerts), "alerts": emergency_alerts}

@app.get("/api/emergency/latest_pending")
def get_latest_pending_alert():
    """
    Returns latest pending emergency crash alert, augmented with countdown & proactive risk warnings.
    """
    gps = latest_gps.get("VH001", {})
    lat = gps.get("latitude")
    lon = gps.get("longitude")
    speed = gps.get("speed_kmh", 0.0)
    risk_info = risk_engine.assess_risk(lat, lon, speed_kmh=speed)
    countdown_info = blackbox_mgr.get_evaluation_status()

    for a in emergency_alerts:
        if a["status"] in ["PENDING_DISPATCH", "COUNTDOWN_VERIFYING"]:
            return {
                "has_pending": True,
                "alert": a,
                "countdown": countdown_info,
                "proactive_risk": risk_info
            }
    return {
        "has_pending": False,
        "alert": None,
        "countdown": countdown_info,
        "proactive_risk": risk_info
    }

@app.post("/api/emergency/alerts/{alert_id}/acknowledge")
@app.post("/api/emergency/acknowledge/{alert_id}")
def acknowledge_alert(alert_id: str):
    """
    For the Android app to mark an alert as SMS SENT.
    """
    for a in emergency_alerts:
        if a["alert_id"] == alert_id:
            a["status"] = "SENT_BY_ANDROID_APP"
            print(f"[ANDROID APP] Successfully sent SMS for {alert_id}")
            return {"status": "updated", "alert": a}
    raise HTTPException(status_code=404, detail="Alert ID not found")

@app.post("/api/config/messaging_url")
def update_messaging_url(cfg: PartnerConfig):
    messaging_config["partner_emergency_url"] = cfg.url
    print(f"[CONFIG] Updated Teammate Messaging URL -> {cfg.url}")
    return {"status": "updated", "partner_emergency_url": cfg.url}

@app.get("/api/config/messaging_url")
def get_messaging_url():
    return messaging_config

@app.post("/api/emergency/test_forward")
def test_forward_emergency():
    """
    Test endpoint to simulate sending POST /emergency to teammate's messaging backend with live GPS coordinates.
    """
    now = time.time()
    formatted_dt = time.strftime("%d %B %Y, %I:%M %p", time.localtime(now))
    gps_data = latest_gps.get("VH001", {})
    lat = gps_data.get("latitude", 23.0305)
    lon = gps_data.get("longitude", 72.5650)
    speed = gps_data.get("speed_kmh", 35.0)
    maps_link = f"https://www.google.com/maps?q={lat},{lon}" if lat and lon else "https://maps.google.com"
    place = get_place_name(lat, lon)
    hosp = find_nearest_hospital(lat, lon)
    forward_to_partner_messaging(
        hospital=hosp,
        relative=DEFAULT_RELATIVE,
        date_time=formatted_dt,
        place=place,
        lat=lat,
        lon=lon,
        maps_link=maps_link,
        speed=speed,
        peak_value=32.5
    )
    return {
        "status": "dispatched",
        "target_url": messaging_config["partner_emergency_url"],
        "hospital": hosp["name"],
        "relative_phone": DEFAULT_RELATIVE["phone"],
        "latitude": lat,
        "longitude": lon,
        "google_maps_url": maps_link,
        "place": place
    }

@app.get("/api/status")
def get_status():
    return {
        "status": "online",
        "active_devices": list(latest_gps.keys()),
        "total_events_logged": len(events_log),
        "total_emergency_alerts": len(emergency_alerts),
        "uptime": time.time()
    }

# ============================================================================
# LIVE WEB MONITORING DASHBOARD (GET /)
# ============================================================================
@app.get("/", response_class=HTMLResponse)
def live_dashboard():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>TECHNEXA 2026 - Smart Road Safety & ITS Command Center</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Leaflet CSS -->
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <style>
            body { background: #0b0f19; color: #f1f5f9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
            .card { background: #151d30; border: 1px solid #1e293b; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4); }
            #map { height: 420px; border-radius: 10px; border: 1px solid #334155; }
            .badge-braking { background: #ef4444; }
            .badge-accel { background: #3b82f6; }
            .badge-corner { background: #f59e0b; }
            .badge-pothole { background: #8b5cf6; }
            .badge-collision { background: #dc2626; animation: pulse 1s infinite; }
            @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
            .mono { font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; }
            .score-circle {
                width: 90px; height: 90px; border-radius: 50%;
                display: flex; flex-direction: column; align-items: center; justify-content: center;
                margin: 0 auto; font-weight: bold; font-size: 26px; border: 4px solid #10b981; color: #10b981;
            }
            .warning-banner { display: none; animation: pulse 1.2s infinite; font-weight: bold; }
        </style>
    </head>
    <body class="p-2 p-md-3">
        <div class="container-fluid">
            <!-- Top Command Header -->
            <div class="d-flex flex-wrap justify-content-between align-items-center mb-3 pb-2 border-bottom border-secondary">
                <div>
                    <h2 class="h4 mb-0 text-info fw-bold">TECHNEXA 2026 — Smart Road Safety & ITS Platform</h2>
                    <p class="text-secondary small mb-0">Edge IoT (ESP32) • Real-Time GPS Fusion • Predictive Risk AI • Municipal Road Quality</p>
                </div>
                <div class="d-flex align-items-center gap-2 mt-2 mt-md-0">
                    <button class="btn btn-sm btn-outline-warning" id="sim-btn" onclick="toggleSimulation()">▶️ Demo Drive</button>
                    <button class="btn btn-sm btn-outline-danger" onclick="triggerTestCrash()">💥 Simulate Crash</button>
                    <button class="btn btn-sm btn-outline-info" onclick="viewLatestBlackbox()">📋 Crash Blackbox</button>
                    <span class="badge bg-success py-2 px-3 fs-6" id="server-status">LIVE SYSTEM ACTIVE</span>
            </div>

            <!-- Live Android Phone Telemetry Status Bar -->
            <div class="card p-2 mb-3 border-info" style="background: #0f1e36;">
                <div class="d-flex flex-wrap justify-content-between align-items-center">
                    <div class="d-flex align-items-center gap-2">
                        <span class="fs-5">📱</span>
                        <strong class="text-light">Live Android Telemetry:</strong>
                        <span id="phone-status-badge" class="badge bg-secondary">⚪ WAITING FOR PHONE STREAM</span>
                    </div>
                    <div class="d-flex align-items-center gap-3 mt-1 mt-md-0 small">
                        <div><span class="text-muted">Target Endpoint:</span> <span class="mono text-info">POST /api/gps</span></div>
                        <div><span class="text-muted">Coords:</span> <span id="phone-coords-display" class="mono text-warning">Awaiting stream...</span></div>
                        <div><span class="text-muted">Speed:</span> <span id="phone-speed-display" class="mono text-success">-- km/h</span></div>
                    </div>
                </div>
            </div>

            <!-- Proactive Hazard Warning Banner -->
            <div id="proactive-alert-bar" class="alert alert-danger warning-banner py-2 px-3 mb-3 d-flex align-items-center justify-content-between">
                <div>
                    <span class="fs-5 me-2">⚠️</span>
                    <span id="warning-text">CAUTION: Entering High-Risk Accident Zone!</span>
                </div>
                <span class="badge bg-dark" id="warning-level">CRITICAL RISK</span>
            </div>

            <!-- Dead Man's Protocol Crash Countdown Alert Banner -->
            <div id="crash-countdown-bar" class="alert alert-danger p-3 mb-3 shadow-lg" style="display:none; background: #581c87; border: 2px solid #c084fc; border-radius: 12px;">
                <div class="d-flex flex-wrap justify-content-between align-items-center">
                    <div>
                        <h5 class="mb-1 text-white fw-bold">🚨 SEVERE CRASH DETECTED — DEAD MAN'S PROTOCOL ACTIVE</h5>
                        <div class="text-light small">
                            Incapacitated Rider Kinematic Check in progress. Emergency SMS dispatches in: 
                            <span class="fs-4 fw-bold text-warning mono" id="countdown-timer-sec">20.0s</span>
                        </div>
                        <div class="small text-secondary mt-1">If this is a low-speed tip-over, kickstand drop, or false alarm, tap below:</div>
                    </div>
                    <div class="mt-2 mt-md-0 d-flex gap-2">
                        <button class="btn btn-success fw-bold px-3 py-2" onclick="cancelFalseAlarm()">🟢 I AM OK — CANCEL DISPATCH</button>
                        <button class="btn btn-outline-light px-3 py-2" onclick="viewLatestBlackbox()">📋 View Crash Blackbox</button>
                    </div>
                </div>
            </div>

            <div class="row g-3">
                <!-- Left Control Column -->
                <div class="col-lg-4">
                    <!-- Driver Safety Scorecard Card (4-Pillar Telematics) -->
                    <div class="card p-3 mb-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <div>
                                <h6 class="text-light mb-0">🚗 Driver Safety Index (4 Pillars)</h6>
                                <span class="small text-warning fw-bold" id="driver-tier-text">PLATINUM SAFE</span>
                            </div>
                            <div class="text-end">
                                <span class="badge bg-success" id="driver-profile-badge">EXCELLENT</span>
                                <div class="small mono text-info mt-1" id="driver-trend">➡️ STABLE</div>
                            </div>
                        </div>
                        <div class="row align-items-center my-2">
                            <div class="col-5 text-center">
                                <div class="score-circle" id="score-circle-elem">
                                    <span id="driver-score-val">100</span>
                                    <span style="font-size: 10px; font-weight: normal; margin-top: -4px;">/ 100</span>
                                </div>
                                <div class="small text-success mt-1 fw-bold" id="insurance-discount-badge">25% Discount</div>
                            </div>
                            <div class="col-7">
                                <!-- 4 Sub-Pillars -->
                                <div class="mb-1">
                                    <div class="d-flex justify-content-between small text-secondary">
                                        <span>Smoothness:</span><strong id="pillar-smooth-val" class="text-light">100%</strong>
                                    </div>
                                    <div class="progress" style="height: 5px; background: #0f172a;">
                                        <div id="pillar-smooth-bar" class="progress-bar bg-info" style="width: 100%;"></div>
                                    </div>
                                </div>
                                <div class="mb-1">
                                    <div class="d-flex justify-content-between small text-secondary">
                                        <span>Cornering:</span><strong id="pillar-corner-val" class="text-light">100%</strong>
                                    </div>
                                    <div class="progress" style="height: 5px; background: #0f172a;">
                                        <div id="pillar-corner-bar" class="progress-bar bg-warning" style="width: 100%;"></div>
                                    </div>
                                </div>
                                <div class="mb-1">
                                    <div class="d-flex justify-content-between small text-secondary">
                                        <span>Speed Limit:</span><strong id="pillar-speed-val" class="text-light">100%</strong>
                                    </div>
                                    <div class="progress" style="height: 5px; background: #0f172a;">
                                        <div id="pillar-speed-bar" class="progress-bar bg-success" style="width: 100%;"></div>
                                    </div>
                                </div>
                                <div>
                                    <div class="d-flex justify-content-between small text-secondary">
                                        <span>Vigilance:</span><strong id="pillar-vigil-val" class="text-light">100%</strong>
                                    </div>
                                    <div class="progress" style="height: 5px; background: #0f172a;">
                                        <div id="pillar-vigil-bar" class="progress-bar bg-primary" style="width: 100%;"></div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="alert alert-dark p-2 border-secondary small my-2" style="background:#0f172a;">
                            <div class="text-info fst-italic" id="driver-tip">Keep up the smooth driving!</div>
                        </div>
                        <div class="row text-center mt-1 pt-1 border-top border-secondary small">
                            <div class="col-4"><span class="text-muted">Braking:</span> <strong id="cnt-braking" class="text-danger">0</strong></div>
                            <div class="col-4"><span class="text-muted">Swerves:</span> <strong id="cnt-cornering" class="text-warning">0</strong></div>
                            <div class="col-4"><span class="text-muted">Surges:</span> <strong id="cnt-accel" class="text-info">0</strong></div>
                        </div>
                    </div>

                    <!-- Predictive Accident Risk Meter -->
                    <div class="card p-3 mb-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <h6 class="text-light mb-0">🎯 Accident-Risk Prediction Engine</h6>
                            <span class="badge bg-success" id="risk-level-badge">LOW RISK</span>
                        </div>
                        <div class="d-flex justify-content-between align-items-center mb-1">
                            <span class="small text-muted">Accident Probability:</span>
                            <span class="fw-bold mono fs-5 text-info" id="risk-score-val">10.0%</span>
                        </div>
                        <div class="progress mb-3" style="height: 10px; background: #0f172a;">
                            <div class="progress-bar bg-success" id="risk-progress-bar" role="progressbar" style="width: 10%;"></div>
                        </div>
                        <div class="small mb-1"><strong>Nearest Blackspot:</strong> <span id="nearest-bs-name" class="text-warning">Scanning...</span></div>
                        <div class="small mb-1"><strong>Distance to Hazard:</strong> <span id="nearest-bs-dist" class="mono text-info">-- m</span></div>
                        <div class="small"><strong>Speed vs Limit:</strong> <span id="speed-vs-limit" class="mono text-success">0.0 km/h (Limit: 50 km/h)</span></div>
                    </div>

                    <!-- Autonomous Road Quality Index (RQI) -->
                    <div class="card p-3 mb-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <h6 class="text-light mb-0">🕳️ Municipal Road Quality (Civic ITS)</h6>
                            <span class="badge bg-warning text-dark" id="rqi-grade-badge">Grade B</span>
                        </div>
                        <div class="small mb-1"><strong>Hazards Mapped:</strong> <span id="potholes-count" class="mono text-warning">0 clusters</span></div>
                        <div class="small mb-2"><strong>Critical Road Defects:</strong> <span id="critical-potholes-count" class="mono text-danger">0</span></div>
                        <div class="small text-muted fst-italic">Crowdsourced real-time via vehicle vertical jerk derivative shocks (>300 m/s³).</div>
                    </div>

                    <!-- Emergency Message Dispatch Queue -->
                    <div class="card p-3 border-danger">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <h6 class="text-danger mb-0">🚨 Emergency Crash Queue</h6>
                            <span class="badge bg-danger" id="alert-count">0</span>
                        </div>
                        <div id="emergency-box" class="small text-secondary">
                            No active collision alerts. Normal monitoring.
                        </div>
                    </div>
                </div>

                <!-- Right Map & Telemetry Column -->
                <div class="col-lg-8">
                    <!-- Interactive Leaflet Map -->
                    <div class="card p-3 mb-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <h6 class="text-light mb-0">🗺️ Live Geospatial Blackspots & Vehicle Heatmap</h6>
                            <div class="d-flex align-items-center small text-muted">
                                <span class="badge bg-danger me-1">🔥 Blackspots</span>
                                <span class="badge bg-purple me-1" style="background:#8b5cf6;">🕳️ Potholes</span>
                                <span class="badge bg-primary me-2">🚗 Live Vehicle</span>
                                <button class="btn btn-sm btn-outline-info py-0 px-2" onclick="fitAllBlackspots()">🔍 Focus Blackspots</button>
                            </div>
                        </div>
                        <div id="map"></div>
                    </div>

                    <!-- Live Event Stream from ESP32 -->
                    <div class="card p-3">
                        <div class="d-flex justify-content-between align-items-center border-bottom pb-2 border-secondary mb-2">
                            <h6 class="text-light mb-0">📡 Live ESP32 Edge Ingestion Stream</h6>
                            <span class="text-secondary small" id="event-counter">0 events logged</span>
                        </div>
                        <div class="table-responsive" style="max-height: 240px; overflow-y: auto;">
                            <table class="table table-dark table-hover align-middle mb-0 small">
                                <thead>
                                    <tr class="text-secondary">
                                        <th>Time</th>
                                        <th>Event Type</th>
                                        <th>Severity</th>
                                        <th>Peak Value</th>
                                        <th>Duration</th>
                                        <th>GPS Location</th>
                                    </tr>
                                </thead>
                                <tbody id="events-table-body">
                                    <tr><td colspan="6" class="text-center text-muted py-3">Waiting for ESP32 Wi-Fi stream... (trigger an event on hardware)</td></tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Leaflet JS + Leaflet Heat -->
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>

        <script>
            // 1. Initialize Leaflet Map centered on Ahmedabad / Gujarat highway corridor
            const defaultLat = 23.0305;
            const defaultLon = 72.5650;
            const map = L.map('map').setView([defaultLat, defaultLon], 12);

            // OpenStreetMap Standard Tiles (100% Free, Zero Watermark / No API Key required)
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
                maxZoom: 19
            }).addTo(map);

            let heatLayer = null;
            let vehicleMarker = null;
            let simMarker = null;
            let potholeMarkers = [];
            let blackspotMarkers = [];
            let allHazardBounds = null;

            function fitAllBlackspots() {
                if (allHazardBounds && allHazardBounds.isValid()) {
                    map.fitBounds(allHazardBounds, {padding: [35, 35]});
                }
            }

            // Real Android Phone Marker Icon (Cyan Beacon with Phone Icon)
            const carIcon = L.divIcon({
                className: 'custom-car-icon',
                html: '<div style="background:#0284c7; width:30px; height:30px; border-radius:50%; border:3px solid #38bdf8; box-shadow:0 0 16px #38bdf8; display:flex; align-items:center; justify-content:center; color:white; font-size:14px; font-weight:bold;">📱</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            // Simulator Marker Icon (Amber Beacon with Car Icon)
            const simIcon = L.divIcon({
                className: 'custom-sim-icon',
                html: '<div style="background:#d97706; width:30px; height:30px; border-radius:50%; border:3px solid #fde047; box-shadow:0 0 16px #fde047; display:flex; align-items:center; justify-content:center; color:black; font-size:14px; font-weight:bold;">🚗</div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            // 2. Load Heatmap Layer & Blackspot Danger Zones
            async function loadHeatmap() {
                try {
                    const res = await fetch('/api/risk/heatmap');
                    if (res.ok) {
                        const data = await res.json();
                        
                        // A. Thermal Heatmap Layer (High-density multi-point dispersion)
                        if (heatLayer) map.removeLayer(heatLayer);
                        heatLayer = L.heatLayer(data.points, {
                            radius: 40,
                            blur: 18,
                            maxZoom: 16,
                            minOpacity: 0.60,
                            gradient: {
                                0.2: '#2563eb',  // vibrant blue
                                0.45: '#10b981', // emerald green
                                0.65: '#facc15', // yellow
                                0.82: '#f97316', // orange
                                1.0: '#ef4444'   // bright red
                            }
                        }).addTo(map);

                        // B. Blackspot Danger Circles & Hotspot Pins
                        blackspotMarkers.forEach(m => map.removeLayer(m));
                        blackspotMarkers = [];

                        const bounds = L.latLngBounds([]);

                        if (data.blackspot_zones) {
                            data.blackspot_zones.forEach(b => {
                                bounds.extend([b.lat, b.lon]);

                                // 1. Semi-transparent danger zone circle matching physical radius
                                const circle = L.circle([b.lat, b.lon], {
                                    radius: b.radius_m,
                                    color: b.color || '#ef4444',
                                    fillColor: b.color || '#ef4444',
                                    fillOpacity: 0.22,
                                    weight: 2,
                                    dashArray: '5, 5'
                                }).addTo(map);

                                // 2. Danger hotspot icon
                                const pin = L.divIcon({
                                    className: 'blackspot-pin',
                                    html: `<div style="background:#ef4444; color:white; width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:bold; border:2px solid white; box-shadow:0 0 10px #ef4444; cursor:pointer;">🔥</div>`,
                                    iconSize: [26, 26],
                                    iconAnchor: [13, 13]
                                });
                                const marker = L.marker([b.lat, b.lon], {icon: pin}).addTo(map);
                                marker.bindPopup(`
                                    <div style="min-width:210px; color:#0f172a;">
                                        <h6 class="mb-1 text-danger fw-bold">🔥 ${b.name}</h6>
                                        <span class="badge bg-danger mb-1">${b.hazard_type}</span><br>
                                        <div class="small mt-1">
                                            <strong>Historical Crashes:</strong> ${b.historical_crashes} (${b.fatalities} Fatalities)<br>
                                            <strong>Severity Index:</strong> ${b.severity_weight}x Multiplier<br>
                                            <strong>Speed Limit:</strong> ${b.speed_limit_kmh} km/h<br>
                                            <strong>Geofence Radius:</strong> ${b.radius_m}m
                                        </div>
                                    </div>
                                `);

                                blackspotMarkers.push(circle);
                                blackspotMarkers.push(marker);
                            });
                        }

                        if (bounds.isValid()) {
                            allHazardBounds = bounds;
                            // If vehicle is not live yet, automatically frame all blackspots
                            if (!vehicleMarker) {
                                map.fitBounds(bounds, {padding: [30, 30], maxZoom: 13});
                            }
                        }
                    }
                } catch(e) { console.error('Heatmap load err:', e); }
            }

            // 3. Load Pothole Markers
            async function loadPotholes() {
                try {
                    const res = await fetch('/api/hazards/potholes');
                    if (res.ok) {
                        const data = await res.json();
                        document.getElementById('rqi-grade-badge').textContent = data.road_quality_grade.split('(')[0];
                        document.getElementById('potholes-count').textContent = `${data.confirmed_potholes} confirmed (${data.total_hazards_logged} total)`;
                        document.getElementById('critical-potholes-count').textContent = data.critical_defects;

                        potholeMarkers.forEach(m => map.removeLayer(m));
                        potholeMarkers = [];

                        data.hazards.forEach(h => {
                            const isCrit = h.severity === 'CRITICAL_DEFECT';
                            const m = L.circleMarker([h.lat, h.lon], {
                                radius: isCrit ? 9 : 6,
                                fillColor: isCrit ? '#ef4444' : '#a855f7',
                                color: '#ffffff',
                                weight: 1.5,
                                fillOpacity: 0.85
                            }).addTo(map);
                            m.bindPopup(`<strong>${h.address}</strong><br>Severity: ${h.severity}<br>Hits: ${h.hit_count}<br>Peak Jerk: ${h.peak_jerk} m/s³`);
                            potholeMarkers.push(m);
                        });
                    }
                } catch(e) { console.error('Potholes load err:', e); }
            }

            // 4. Main Dashboard Polling Update Loop
            async function updateDashboard() {
                try {
                    // A. Fetch Live Android GPS Telemetry
                    const gpsRes = await fetch('/api/gps/latest?device_id=VH001');
                    if (gpsRes.ok) {
                        const gps = await gpsRes.json();
                        const lat = gps.latitude;
                        const lon = gps.longitude;
                        const spd = gps.speed_kmh || 0.0;
                        const isLive = gps.is_live;
                        const lastUpdated = gps.last_updated;

                        const badge = document.getElementById('phone-status-badge');
                        const coordsElem = document.getElementById('phone-coords-display');
                        const speedElem = document.getElementById('phone-speed-display');

                        if (isLive && lastUpdated > 0) {
                            const ago = Math.max(0, Math.round((Date.now() / 1000) - lastUpdated));
                            badge.className = 'badge bg-success';
                            badge.textContent = `🟢 STREAMING LIVE (${ago}s ago)`;
                            coordsElem.textContent = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
                            speedElem.textContent = `${spd.toFixed(1)} km/h`;

                            if (lat && lon) {
                                if (!vehicleMarker) {
                                    vehicleMarker = L.marker([lat, lon], {icon: carIcon}).addTo(map);
                                    vehicleMarker.bindPopup("<strong>📱 Live Android Phone (VH001)</strong><br>Speed: " + spd.toFixed(1) + " km/h");
                                    map.setView([lat, lon], 15);
                                } else {
                                    vehicleMarker.setLatLng([lat, lon]);
                                    vehicleMarker.setPopupContent("<strong>📱 Live Android Phone (VH001)</strong><br>Speed: " + spd.toFixed(1) + " km/h");
                                }
                            }
                        } else {
                            badge.className = 'badge bg-secondary';
                            badge.textContent = '⚪ WAITING FOR PHONE STREAM';
                            coordsElem.textContent = 'Awaiting POST /api/gps...';
                            speedElem.textContent = '-- km/h';
                        }
                    }

                    // B. Fetch Risk Engine
                    const riskRes = await fetch('/api/risk/current');
                    if (riskRes.ok) {
                        const risk = await riskRes.json();
                        const score = risk.risk_score;
                        const level = risk.risk_level;

                        document.getElementById('risk-score-val').textContent = `${score}%`;
                        const pbar = document.getElementById('risk-progress-bar');
                        pbar.style.width = `${score}%`;

                        if (score >= 80) { pbar.className = 'progress-bar bg-danger'; }
                        else if (score >= 60) { pbar.className = 'progress-bar bg-warning'; }
                        else if (score >= 35) { pbar.className = 'progress-bar bg-info'; }
                        else { pbar.className = 'progress-bar bg-success'; }

                        const rBadge = document.getElementById('risk-level-badge');
                        rBadge.textContent = `${level} RISK`;
                        rBadge.className = `badge bg-${risk.badge_color}`;

                        document.getElementById('nearest-bs-name').textContent = risk.nearest_blackspot || 'None';
                        document.getElementById('nearest-bs-dist').textContent = risk.distance_to_blackspot_m ? `${risk.distance_to_blackspot_m} m` : '-- m';
                        document.getElementById('speed-vs-limit').textContent = `${risk.speed_kmh} km/h (Limit: ${risk.speed_limit_kmh} km/h)`;

                        // Proactive Alert Banner
                        const alertBar = document.getElementById('proactive-alert-bar');
                        if (risk.warnings && risk.warnings.length > 0) {
                            alertBar.style.display = 'flex';
                            document.getElementById('warning-text').textContent = risk.warnings[0];
                            document.getElementById('warning-level').textContent = `${level} RISK`;
                        } else {
                            alertBar.style.display = 'none';
                        }
                    }

                    // C. Fetch Driver Safety Score (4-Pillar Telematics)
                    const scoreRes = await fetch('/api/safety/score');
                    if (scoreRes.ok) {
                        const sData = await scoreRes.json();
                        document.getElementById('driver-score-val').textContent = Math.round(sData.score);
                        document.getElementById('driver-tier-text').textContent = sData.tier || 'PLATINUM SAFE';
                        document.getElementById('driver-profile-badge').textContent = sData.profile;
                        document.getElementById('driver-profile-badge').className = `badge bg-${sData.badge_color}`;
                        
                        const trendIcon = sData.trend === 'IMPROVING' ? '↗️ IMPROVING' : (sData.trend === 'DECLINING' ? '↘️ DECLINING' : '➡️ STABLE');
                        document.getElementById('driver-trend').textContent = trendIcon;
                        document.getElementById('driver-tip').textContent = sData.tip;

                        if (sData.insurance) {
                            document.getElementById('insurance-discount-badge').textContent = `${sData.insurance.discount_percent}% Safe Discount`;
                        }

                        // 4 Sub-Pillars
                        if (sData.pillars) {
                            document.getElementById('pillar-smooth-val').textContent = `${Math.round(sData.pillars.smoothness)}%`;
                            document.getElementById('pillar-smooth-bar').style.width = `${sData.pillars.smoothness}%`;

                            document.getElementById('pillar-corner-val').textContent = `${Math.round(sData.pillars.cornering)}%`;
                            document.getElementById('pillar-corner-bar').style.width = `${sData.pillars.cornering}%`;

                            document.getElementById('pillar-speed-val').textContent = `${Math.round(sData.pillars.speed_compliance)}%`;
                            document.getElementById('pillar-speed-bar').style.width = `${sData.pillars.speed_compliance}%`;

                            document.getElementById('pillar-vigil-val').textContent = `${Math.round(sData.pillars.vigilance)}%`;
                            document.getElementById('pillar-vigil-bar').style.width = `${sData.pillars.vigilance}%`;
                        }

                        const circ = document.getElementById('score-circle-elem');
                        if (sData.score >= 88) circ.style.borderColor = circ.style.color = '#10b981';
                        else if (sData.score >= 70) circ.style.borderColor = circ.style.color = '#0ea5e9';
                        else if (sData.score >= 50) circ.style.borderColor = circ.style.color = '#f59e0b';
                        else circ.style.borderColor = circ.style.color = '#ef4444';

                        document.getElementById('cnt-braking').textContent = sData.counts.HARSH_BRAKING || 0;
                        document.getElementById('cnt-cornering').textContent = sData.counts.AGGRESSIVE_CORNERING || 0;
                        document.getElementById('cnt-accel').textContent = sData.counts.HARSH_ACCELERATION || 0;
                    }

                    // D. Fetch Events Table
                    const evRes = await fetch('/api/events');
                    if (evRes.ok) {
                        const evData = await evRes.json();
                        document.getElementById('event-counter').textContent = `${evData.count} events logged`;
                        const tbody = document.getElementById('events-table-body');
                        if (evData.events && evData.events.length > 0) {
                            tbody.innerHTML = evData.events.slice(0, 15).map(e => {
                                let badgeClass = 'bg-secondary';
                                if (e.event === 'HARSH_BRAKING') badgeClass = 'badge-braking';
                                else if (e.event === 'HARSH_ACCELERATION') badgeClass = 'badge-accel';
                                else if (e.event === 'AGGRESSIVE_CORNERING') badgeClass = 'badge-corner';
                                else if (e.event === 'POTHOLE') badgeClass = 'badge-pothole';
                                else if (e.event === 'COLLISION' || e.event === 'ROLLOVER_TILT') badgeClass = 'badge-collision';

                                const timeStr = new Date(e.received_at * 1000).toLocaleTimeString();
                                const gpsStr = (e.latitude && e.longitude) ? `${e.latitude.toFixed(4)}, ${e.longitude.toFixed(4)}` : 'Pending GPS';

                                return `
                                    <tr>
                                        <td class="mono small text-muted">${timeStr}</td>
                                        <td><span class="badge ${badgeClass} py-1 px-2">${e.event}</span></td>
                                        <td><strong>${e.severity.toFixed(2)}</strong></td>
                                        <td class="mono text-info">${e.peak_value.toFixed(2)}</td>
                                        <td class="small text-muted">${e.duration_ms || 0} ms</td>
                                        <td class="mono small text-warning">${gpsStr}</td>
                                    </tr>
                                `;
                            }).join('');
                        }
                    }

                    // E. Fetch Emergency Alerts
                    const emRes = await fetch('/api/emergency/alerts');
                    if (emRes.ok) {
                        const emData = await emRes.json();
                        document.getElementById('alert-count').textContent = emData.count;
                        const box = document.getElementById('emergency-box');
                        if (emData.alerts && emData.alerts.length > 0) {
                            box.innerHTML = emData.alerts.slice(0, 2).map(a => `
                                <div class="alert alert-danger p-2 mb-2">
                                    <div class="d-flex justify-content-between">
                                        <strong>${a.alert_id}</strong>
                                        <span class="badge bg-warning text-dark">${a.status}</span>
                                    </div>
                                    <div class="small mt-1"><strong>Impact:</strong> ${a.impact_peak_ms2.toFixed(1)} m/s² | <strong>Speed:</strong> ${a.speed_kmh.toFixed(1)} km/h</div>
                                    <div class="small"><strong>Hospital:</strong> ${a.hospital_name || a.nearest_hospital.name}</div>
                                    <hr class="my-1 border-danger">
                                    <div class="small text-white mono" style="white-space: pre-wrap; font-size: 11px;">${a.sms_body || a.prepared_sms_text}</div>
                                </div>
                            `).join('');
                        } else {
                            box.innerHTML = '<div class="text-muted small">No active collision alerts. Normal monitoring.</div>';
                        }
                    }

                } catch (err) {
                    console.error("Dashboard poll error:", err);
                }
            }

            // 5. Live Simulation Player for Hackathon Demonstrations
            let simInterval = null;
            const simRoute = [
                { lat: 23.0250, lon: 72.5020, speed: 45.0 },
                { lat: 23.0265, lon: 72.5040, speed: 52.0 },
                { lat: 23.0280, lon: 72.5055, speed: 65.0 }, // Approaching Iskcon overpass
                { lat: 23.0298, lon: 72.5074, speed: 72.0 }, // Inside Iskcon Blackspot BS_001 (Overspeeding 72 in 50)
                { lat: 23.0315, lon: 72.5090, speed: 35.0 }, // Hits Pothole PH_001
                { lat: 23.0330, lon: 72.5110, speed: 48.0 },
                { lat: 23.0360, lon: 72.5130, speed: 50.0 }
            ];
            let simIndex = 0;

            function toggleSimulation() {
                const btn = document.getElementById('sim-btn');
                if (simInterval) {
                    clearInterval(simInterval);
                    simInterval = null;
                    btn.textContent = '▶️ Demo Drive';
                    btn.className = 'btn btn-sm btn-outline-warning';
                    if (simMarker) {
                        map.removeLayer(simMarker);
                        simMarker = null;
                    }
                } else {
                    simIndex = 0;
                    btn.textContent = '⏹️ Stop Simulation';
                    btn.className = 'btn btn-sm btn-danger';
                    simInterval = setInterval(async () => {
                        if (simIndex >= simRoute.length) {
                            toggleSimulation();
                            return;
                        }
                        const step = simRoute[simIndex++];
                        await fetch('/api/simulation/drive_step', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(step)
                        });
                        if (!simMarker) {
                            simMarker = L.marker([step.lat, step.lon], {icon: simIcon}).addTo(map);
                            simMarker.bindPopup("<strong>🚗 Demo Simulator Vehicle</strong><br>Speed: " + step.speed + " km/h");
                        } else {
                            simMarker.setLatLng([step.lat, step.lon]);
                            simMarker.setPopupContent("<strong>🚗 Demo Simulator Vehicle</strong><br>Speed: " + step.speed + " km/h");
                        }
                        updateDashboard();
                    }, 2500);
                }
            }

            // 6. Dead Man's Protocol & False Alarm Cancellation
            async function cancelFalseAlarm() {
                const res = await fetch('/api/emergency/cancel', {method: 'POST'});
                const data = await res.json();
                document.getElementById('crash-countdown-bar').style.display = 'none';
                alert("✅ False Alarm Cancelled! Dead Man's Protocol aborted emergency SMS dispatch.");
                updateDashboard();
            }

            async function checkCountdown() {
                try {
                    const res = await fetch('/api/emergency/countdown');
                    if (res.ok) {
                        const data = await res.json();
                        const bar = document.getElementById('crash-countdown-bar');
                        if (data.has_active_countdown && data.status === 'COUNTDOWN_VERIFYING') {
                            bar.style.display = 'block';
                            document.getElementById('countdown-timer-sec').textContent = `${data.remaining_sec}s`;
                        } else {
                            bar.style.display = 'none';
                        }
                    }
                } catch(e) {}
            }

            // 7. View Digital Crash Blackbox Forensic Report
            async function viewLatestBlackbox() {
                try {
                    const res = await fetch('/api/emergency/blackbox/latest');
                    if (res.ok) {
                        const bb = await res.json();
                        let timelineRows = (bb.telemetry_timeline || []).map(t => `
                            <tr>
                                <td class="mono small">${t.time_rel_sec}</td>
                                <td class="mono small text-info">${t.speed_kmh} km/h</td>
                                <td class="mono small text-warning">${t.g_force}g</td>
                                <td class="mono small text-muted">${t.tilt_deg}°</td>
                            </tr>
                        `).join('');

                        document.getElementById('blackbox-modal-body').innerHTML = `
                            <div class="alert alert-dark p-2 border-secondary small mb-3">
                                <strong>Digital FIR Telemetry ID:</strong> <span class="mono text-warning">${bb.blackbox_id}</span> | 
                                <strong>Status:</strong> <span class="badge bg-success">Tamper-Evident Hash Verified</span>
                            </div>
                            <div class="row g-2 mb-3 text-center">
                                <div class="col-4">
                                    <div class="p-2 border border-secondary rounded" style="background:#0f172a;">
                                        <span class="text-secondary small">Pre-Crash Speed</span>
                                        <h4 class="text-info mono mb-0">${bb.pre_crash_speed_kmh} km/h</h4>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="p-2 border border-secondary rounded" style="background:#0f172a;">
                                        <span class="text-secondary small">Delta-V Shock</span>
                                        <h4 class="text-danger mono mb-0">${bb.delta_v_kmh} km/h</h4>
                                    </div>
                                </div>
                                <div class="col-4">
                                    <div class="p-2 border border-secondary rounded" style="background:#0f172a;">
                                        <span class="text-secondary small">Impact Force</span>
                                        <h4 class="text-warning mono mb-0">${bb.peak_impact_g}g</h4>
                                    </div>
                                </div>
                            </div>
                            <div class="small mb-3">
                                <div><strong>Impact Vector:</strong> <span class="badge bg-danger">${bb.impact_vector}</span></div>
                                <div class="mt-1"><strong>Predicted Injury Severity (AIS):</strong> <span class="text-warning fw-bold">${bb.injury_risk_prediction}</span></div>
                                <div class="mt-1"><strong>Emergency Trauma Routing:</strong> <span class="text-success">${bb.recommended_trauma_level} (${bb.hospital_name})</span></div>
                            </div>
                            <h6 class="text-light border-bottom border-secondary pb-1 small">5-Second Pre-Crash Telemetry Trajectory:</h6>
                            <div class="table-responsive" style="max-height: 150px; overflow-y:auto;">
                                <table class="table table-dark table-sm mb-0">
                                    <thead><tr class="text-secondary small"><th>Time Offset</th><th>Speed</th><th>G-Force</th><th>Chassis Tilt</th></tr></thead>
                                    <tbody>${timelineRows || '<tr><td colspan="4" class="text-muted">No high-rate points in buffer</td></tr>'}</tbody>
                                </table>
                            </div>
                        `;
                        const modal = new bootstrap.Modal(document.getElementById('blackboxModal'));
                        modal.show();
                    } else {
                        alert("No crash blackbox report compiled yet. Trigger a collision to generate one!");
                    }
                } catch(e) { console.error(e); }
            }

            // 8. Demo Simulator Helper to trigger crash
            async function triggerTestCrash() {
                await fetch('/api/events', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        device_id: 'VH001',
                        event: 'COLLISION',
                        severity: 0.95,
                        peak_value: 38.4,
                        duration_ms: 180
                    })
                });
                updateDashboard();
                checkCountdown();
            }

            loadHeatmap();
            loadPotholes();
            setInterval(updateDashboard, 1500);
            setInterval(checkCountdown, 1000);
            updateDashboard();
        </script>

        <!-- Digital Crash Blackbox Reconstruction Modal -->
        <div class="modal fade" id="blackboxModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content" style="background:#151d30; border:1px solid #334155; color:#f8fafc;">
                    <div class="modal-header border-secondary">
                        <h5 class="modal-title text-info fw-bold">📋 Digital Crash Blackbox & Forensic Reconstruction</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body" id="blackbox-modal-body">
                        Loading forensic reconstruction packet...
                    </div>
                    <div class="modal-footer border-secondary">
                        <span class="small text-muted me-auto">Tamper-Proof IoT Edge Buffer • SHA-256 Verified</span>
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Bootstrap 5 JS Bundle -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    # Bind to 0.0.0.0 so ESP32 on Wi-Fi and teammate's phone can reach it
    uvicorn.run(app, host="0.0.0.0", port=8000)

