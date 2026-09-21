import time
import math
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr

try:
    from ml.risk_engine import risk_engine
    from ml.safety_scorer import driver_scorer
    from ml.pothole_tracker import pothole_tracker
    from ml.blackspots_data import get_all_blackspots
except ImportError:
    from backend.ml.risk_engine import risk_engine
    from backend.ml.safety_scorer import driver_scorer
    from backend.ml.pothole_tracker import pothole_tracker
    from backend.ml.blackspots_data import get_all_blackspots

router = APIRouter(prefix="", tags=["Android App Contract"])

# ============================================================================
# 1. AUTH MODELS & IN-MEMORY STORE
# ============================================================================
class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    confirm_password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AuthUser(BaseModel):
    user_id: str = "USR_98241"
    name: str = "Rahul Sharma"
    email: str = "rahul.sharma@example.com"

class AuthResponse(BaseModel):
    success: bool = True
    message: str = "Authentication successful"
    token: str = "jwt_token_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiVVNSXzk4MjQxIiwicm9sZSI6ImRyaXZlciIsImV4cCI6MTc4OTk5OTk5OX0.signature"
    user: AuthUser

# In-memory users store
USERS_DB: Dict[str, Dict[str, Any]] = {
    "rahul.sharma@example.com": {
        "user_id": "USR_98241",
        "name": "Rahul Sharma",
        "email": "rahul.sharma@example.com",
        "password": "SecurePass@2026",
        "token": "jwt_token_eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.USR_98241.signature"
    }
}

# ============================================================================
# 2. USER PROFILE MODELS & STORE
# ============================================================================
class UserProfileResponse(BaseModel):
    user_id: str
    name: str
    profile_picture_url: str
    email: str
    phone_number: str
    relative_phone_number: str
    age: int
    blood_group: str
    car_plate_number: str

class UpdateProfileRequest(BaseModel):
    profile_picture_base64: Optional[str] = None
    email: str
    password: Optional[str] = None
    phone_number: str
    relative_phone_number: str
    age: int
    blood_group: str
    car_plate_number: str

USER_PROFILE_DATA = {
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

# ============================================================================
# 3. RIDE & NAVIGATION MODELS
# ============================================================================
class StartRideRequest(BaseModel):
    destination: str
    current_lat: float
    current_lon: float

class NavigationAlertItem(BaseModel):
    alert_id: str
    title: str
    instruction: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    distance_ahead_m: int
    category: str  # "ACCIDENT_PRONE", "POTHOLE", "BLIND_CURVE", "SPEED_LIMIT", "NAVIGATION"

class NavigationAlertsResponse(BaseModel):
    destination: str
    origin: str = "Infocity, Gandhinagar"
    distance_km: float
    estimated_time_mins: int
    alerts: List[NavigationAlertItem]

ACTIVE_NAVIGATION: Optional[Dict[str, Any]] = None

# ============================================================================
# 4. HAZARDS & FREQUENT ROUTES MODELS
# ============================================================================
class FrequentRoute(BaseModel):
    route_id: str
    title: str
    origin: str
    destination: str
    trip_count: int
    total_distance_km: float
    total_hazards_count: int

class RouteHazardItem(BaseModel):
    hazard_id: str
    hazard_type: str  # "POTHOLE", "ACCIDENT_BLACKSPOT", "BLIND_CURVE", "WATER_LOGGING"
    title: str
    nearby_location: str
    description: str
    severity: str  # "CRITICAL", "MODERATE", "LOW"
    lat: float
    lon: float

class RouteHazardsDetailResponse(BaseModel):
    route_id: str
    route_title: str
    hazards: List[RouteHazardItem]

# Pre-seeded routes & hazards based on actual Gujarat blackspots
FREQUENT_ROUTES: List[FrequentRoute] = [
    FrequentRoute(
        route_id="ROUTE_GNR_MEH_01",
        title="Gandhinagar to Mehsana",
        origin="Gandhinagar CH Road",
        destination="Mehsana Highway Circle",
        trip_count=28,
        total_distance_km=68.5,
        total_hazards_count=6
    ),
    FrequentRoute(
        route_id="ROUTE_AHM_GNR_02",
        title="Ahmedabad to Gandhinagar",
        origin="Iskcon Crossroad, SG Highway",
        destination="Infocity, Gandhinagar",
        trip_count=45,
        total_distance_km=26.3,
        total_hazards_count=4
    ),
    FrequentRoute(
        route_id="ROUTE_SARKHEJ_03",
        title="Sarkhej to Sanand Industrial Hub",
        origin="Sarkhej Ujala Circle",
        destination="Sanand GIDC Auto Cluster",
        trip_count=14,
        total_distance_km=32.0,
        total_hazards_count=5
    )
]

ROUTE_HAZARDS_STORE: Dict[str, RouteHazardsDetailResponse] = {
    "ROUTE_GNR_MEH_01": RouteHazardsDetailResponse(
        route_id="ROUTE_GNR_MEH_01",
        route_title="Gandhinagar to Mehsana",
        hazards=[
            RouteHazardItem(
                hazard_id="HAZ_001",
                hazard_type="POTHOLE",
                title="Severe Pothole Cluster",
                nearby_location="Near: 50m past S-DMart, Kudasan Crossroad",
                description="Multiple deep surface potholes across middle and right lanes detected by IMU jerk sensor",
                severity="CRITICAL",
                lat=23.1894,
                lon=72.6281
            ),
            RouteHazardItem(
                hazard_id="HAZ_002",
                hazard_type="ACCIDENT_BLACKSPOT",
                title="Chhatral GIDC Highway Junction Blackspot",
                nearby_location="Near: Chhatral Overbridge Exit",
                description="High fatality intersection: heavy industrial container trucks merging without turn signals",
                severity="CRITICAL",
                lat=23.3325,
                lon=72.4389
            ),
            RouteHazardItem(
                hazard_id="HAZ_003",
                hazard_type="BLIND_CURVE",
                title="Sharp S-Curve with Obstructed Visibility",
                nearby_location="Near: Kalol Toll Plaza bypass",
                description="High-speed blind curve; recommended entry speed 40 km/h",
                severity="MODERATE",
                lat=23.2510,
                lon=72.4980
            ),
            RouteHazardItem(
                hazard_id="HAZ_004",
                hazard_type="WATER_LOGGING",
                title="Monsoon Waterlogged Underpass",
                nearby_location="Near: Nandasan Railway Underpass",
                description="Standing water up to 25cm during rains causing hydroplaning risk",
                severity="MODERATE",
                lat=23.4120,
                lon=72.4150
            ),
            RouteHazardItem(
                hazard_id="HAZ_005",
                hazard_type="POTHOLE",
                title="Bridge Expansion Joint Trench",
                nearby_location="Near: Mehsana Southern Bypass Bridge",
                description="Abrupt 7cm asphalt drop causing harsh vertical chassis shock",
                severity="CRITICAL",
                lat=23.5720,
                lon=72.3780
            ),
            RouteHazardItem(
                hazard_id="HAZ_006",
                hazard_type="ACCIDENT_BLACKSPOT",
                title="Civil Hospital Mehsana Ambulance Corridor",
                nearby_location="Near: Radhanpur Road Crossroad",
                description="Frequent emergency vehicle crossing with uncontrolled median gap",
                severity="LOW",
                lat=23.5900,
                lon=72.3900
            )
        ]
    ),
    "ROUTE_AHM_GNR_02": RouteHazardsDetailResponse(
        route_id="ROUTE_AHM_GNR_02",
        route_title="Ahmedabad to Gandhinagar",
        hazards=[
            RouteHazardItem(
                hazard_id="HAZ_101",
                hazard_type="ACCIDENT_BLACKSPOT",
                title="Iskcon Crossroad Blackspot",
                nearby_location="Near: SG Highway BRTS Corridor",
                description="History of 42 crashes: late-night overspeeding and flyover entry conflicts",
                severity="CRITICAL",
                lat=23.0298,
                lon=72.5074
            ),
            RouteHazardItem(
                hazard_id="HAZ_102",
                hazard_type="ACCIDENT_BLACKSPOT",
                title="Vaishno Devi Circle Blackspot",
                nearby_location="Near: Sardar Patel Ring Road Cloverleaf",
                description="High conflict weaving zone between SG Highway and Ring Road traffic",
                severity="CRITICAL",
                lat=23.1315,
                lon=72.5445
            ),
            RouteHazardItem(
                hazard_id="HAZ_103",
                hazard_type="POTHOLE",
                title="Service Road Pothole String",
                nearby_location="Near: Nirma University Gate 2",
                description="Craters on service lane due to monsoon runoff",
                severity="MODERATE",
                lat=23.1250,
                lon=72.5420
            ),
            RouteHazardItem(
                hazard_id="HAZ_104",
                hazard_type="BLIND_CURVE",
                title="Adalaj Tri-Junction Curve",
                nearby_location="Near: Trimandir Approach Cut",
                description="Unsignaled U-turn cut with high pedestrian footfall",
                severity="MODERATE",
                lat=23.1670,
                lon=72.5810
            )
        ]
    )
}

# ============================================================================
# 5. DRIVER SCORE & FINE TICKETS MODELS
# ============================================================================
class FineTicket(BaseModel):
    ticket_id: str
    reason: str
    date: str
    amount: str
    amount_numeric: float
    status: str  # "UNPAID", "PAID", "DISPUTED"
    location: str

class PillarPct(BaseModel):
    smoothness_pct: int
    cornering_pct: int
    speed_compliance_pct: int
    vigilance_pct: int

class DriverScoreResponse(BaseModel):
    overall_score: int
    actuarial_tier: str  # "Platinum Safe", "Gold Standard", "Silver Moderate", "High Risk"
    insurance_discount_pct: int
    trend: str  # "IMPROVING", "STABLE", "DECLINING"
    pillars: PillarPct
    fine_tickets: List[FineTicket]

FINE_TICKETS_STORE: List[FineTicket] = [
    FineTicket(
        ticket_id="TCK-2026-901",
        reason="Overspeeding > 80 km/h at SG Highway",
        date="18 Sep 2026, 04:15 PM",
        amount="₹1,000",
        amount_numeric=1000.0,
        status="UNPAID",
        location="SG Highway Flyover near Vaishno Devi"
    ),
    FineTicket(
        ticket_id="TCK-2026-784",
        reason="Harsh Lane Change Without Indicator",
        date="12 Sep 2026, 09:30 AM",
        amount="₹500",
        amount_numeric=500.0,
        status="PAID",
        location="Kudasan Crossroad, Gandhinagar"
    )
]

# ============================================================================
# 6. HEATMAP MODELS
# ============================================================================
class WeightedPoint(BaseModel):
    lat: float
    lon: float
    weight: float
    location_name: Optional[str] = "Hazard Zone"

class BlackspotZoneItem(BaseModel):
    id: str
    name: str
    lat: float
    lon: float
    radius_m: float
    color: str = "#9D0208"
    historical_crashes: int
    fatalities: int
    speed_limit_kmh: int

class HeatmapContractResponse(BaseModel):
    total_incidents: int
    center_lat: float
    center_lon: float
    weighted_points: List[WeightedPoint]
    blackspot_zones: List[BlackspotZoneItem]


# ============================================================================
# ROUTER ENDPOINTS IMPLEMENTATION
# ============================================================================

# --- 1. AUTH ENDPOINTS ---
@router.post("/api/auth/register", response_model=AuthResponse)
@router.post("/auth/register", response_model=AuthResponse)
def register_user(req: RegisterRequest):
    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    user_id = f"USR_{int(time.time()) % 100000}"
    token = f"jwt_token_{user_id}.{int(time.time())}.technexa_sig"
    
    USERS_DB[req.email.lower()] = {
        "user_id": user_id,
        "name": req.name,
        "email": req.email.lower(),
        "password": req.password,
        "token": token
    }
    
    # Also update profile
    USER_PROFILE_DATA["user_id"] = user_id
    USER_PROFILE_DATA["name"] = req.name
    USER_PROFILE_DATA["email"] = req.email.lower()
    
    return AuthResponse(
        success=True,
        message="User registered successfully",
        token=token,
        user=AuthUser(user_id=user_id, name=req.name, email=req.email.lower())
    )

@router.post("/api/auth/login", response_model=AuthResponse)
@router.post("/auth/login", response_model=AuthResponse)
def login_user(req: LoginRequest):
    email = req.email.lower()
    user_record = USERS_DB.get(email)
    
    # Hackathon permissive login: if user not found, auto-provision
    if not user_record:
        user_id = f"USR_{abs(hash(email)) % 100000}"
        token = f"jwt_token_{user_id}.technexa_sig"
        name = email.split("@")[0].replace(".", " ").title()
        user_record = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "password": req.password,
            "token": token
        }
        USERS_DB[email] = user_record
    elif user_record["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    USER_PROFILE_DATA["user_id"] = user_record["user_id"]
    USER_PROFILE_DATA["name"] = user_record["name"]
    USER_PROFILE_DATA["email"] = user_record["email"]
    
    return AuthResponse(
        success=True,
        message="Authentication successful",
        token=user_record["token"],
        user=AuthUser(
            user_id=user_record["user_id"],
            name=user_record["name"],
            email=user_record["email"]
        )
    )

# --- 2. USER PROFILE ENDPOINTS ---
@router.get("/api/user/profile", response_model=UserProfileResponse)
@router.get("/api/user_profile", response_model=UserProfileResponse)
def get_user_profile():
    return UserProfileResponse(**USER_PROFILE_DATA)

@router.post("/api/user/profile", response_model=UserProfileResponse)
@router.put("/api/user/profile", response_model=UserProfileResponse)
@router.post("/api/update_profile", response_model=UserProfileResponse)
def update_user_profile(req: UpdateProfileRequest):
    USER_PROFILE_DATA["email"] = req.email
    USER_PROFILE_DATA["phone_number"] = req.phone_number
    USER_PROFILE_DATA["relative_phone_number"] = req.relative_phone_number
    USER_PROFILE_DATA["age"] = req.age
    USER_PROFILE_DATA["blood_group"] = req.blood_group
    USER_PROFILE_DATA["car_plate_number"] = req.car_plate_number
    
    if req.profile_picture_base64:
        USER_PROFILE_DATA["profile_picture_url"] = req.profile_picture_base64
        
    return UserProfileResponse(**USER_PROFILE_DATA)

# --- 3. RIDE & NAVIGATION ENDPOINTS ---
@router.post("/api/ride/start", response_model=NavigationAlertsResponse)
@router.post("/api/navigation/start", response_model=NavigationAlertsResponse)
def start_ride(req: StartRideRequest):
    global ACTIVE_NAVIGATION
    
    # Calculate synthetic distance based on coordinates or destination
    dest_lower = req.destination.lower()
    if "mehsana" in dest_lower:
        dist_km = 54.2
        est_mins = 58
        origin = "Infocity, Gandhinagar"
    elif "ahmedabad" in dest_lower:
        dist_km = 26.5
        est_mins = 35
        origin = "Gandhinagar CH Road"
    elif "sanand" in dest_lower:
        dist_km = 42.0
        est_mins = 48
        origin = "SG Highway, Ahmedabad"
    else:
        dist_km = 35.0
        est_mins = 40
        origin = f"Current GPS ({round(req.current_lat, 3)}, {round(req.current_lon, 3)})"
        
    # Generate contextual real-time alerts
    alerts: List[NavigationAlertItem] = [
        NavigationAlertItem(
            alert_id="ALT-001",
            title="Accident Prone Area Ahead",
            instruction="High crash zone near Vaishno Devi circle. Reduce speed to 35 km/h.",
            severity="HIGH",
            distance_ahead_m=350,
            category="ACCIDENT_PRONE"
        ),
        NavigationAlertItem(
            alert_id="ALT-002",
            title="Road Defect: Deep Pothole Cluster",
            instruction="Severe pothole cluster in middle lane 50m ahead. Shift left safely.",
            severity="HIGH",
            distance_ahead_m=50,
            category="POTHOLE"
        ),
        NavigationAlertItem(
            alert_id="ALT-003",
            title="Sharp Blind S-Curve",
            instruction="Approaching unbanked curve near Kalol. Recommended limit 40 km/h.",
            severity="MEDIUM",
            distance_ahead_m=800,
            category="BLIND_CURVE"
        ),
        NavigationAlertItem(
            alert_id="ALT-004",
            title="Regulatory Speed Limit Enforcement",
            instruction="Entering NH-48 commercial corridor. Speed limit enforced at 60 km/h.",
            severity="LOW",
            distance_ahead_m=1200,
            category="SPEED_LIMIT"
        )
    ]
    
    ACTIVE_NAVIGATION = {
        "destination": req.destination,
        "origin": origin,
        "distance_km": dist_km,
        "estimated_time_mins": est_mins,
        "alerts": [a.dict() for a in alerts],
        "start_time": time.time()
    }
    
    return NavigationAlertsResponse(
        destination=req.destination,
        origin=origin,
        distance_km=dist_km,
        estimated_time_mins=est_mins,
        alerts=alerts
    )

@router.get("/api/navigation/alerts", response_model=NavigationAlertsResponse)
def get_navigation_alerts():
    if not ACTIVE_NAVIGATION:
        # Return sensible default route to Mehsana
        dummy_req = StartRideRequest(
            destination="Mehsana Highway Bypass",
            current_lat=23.2156,
            current_lon=72.6369
        )
        return start_ride(dummy_req)
    return NavigationAlertsResponse(**ACTIVE_NAVIGATION)

# --- 4. HAZARDS & FREQUENT ROUTES ENDPOINTS ---
@router.get("/api/hazards/frequently_traveled_routes", response_model=List[FrequentRoute])
@router.get("/api/hazards/frequent-routes", response_model=List[FrequentRoute])
@router.get("/api/hazards/routes", response_model=List[FrequentRoute])
def get_frequently_traveled_routes():
    return FREQUENT_ROUTES

@router.get("/api/hazards/route_hazards_detail", response_model=RouteHazardsDetailResponse)
@router.get("/api/hazards/route-detail", response_model=RouteHazardsDetailResponse)
def get_route_hazards_detail(route_id: Optional[str] = None):
    rid = route_id or "ROUTE_GNR_MEH_01"
    if rid in ROUTE_HAZARDS_STORE:
        return ROUTE_HAZARDS_STORE[rid]
    return ROUTE_HAZARDS_STORE["ROUTE_GNR_MEH_01"]

@router.get("/api/hazards/routes/{route_id}", response_model=RouteHazardsDetailResponse)
def get_route_hazards_by_id(route_id: str):
    if route_id in ROUTE_HAZARDS_STORE:
        return ROUTE_HAZARDS_STORE[route_id]
    return ROUTE_HAZARDS_STORE["ROUTE_GNR_MEH_01"]

# --- 5. DRIVER SCORE & FINE TICKETS ENDPOINTS ---
@router.get("/api/driver/score", response_model=DriverScoreResponse)
@router.get("/api/driver_score", response_model=DriverScoreResponse)
def get_contract_driver_score():
    # Dynamically bind to live 4-pillar telematics safety engine
    profile = driver_scorer.get_profile()
    
    score_int = int(round(profile.get("score", 88.0)))
    raw_tier = profile.get("tier", "PLATINUM SAFE")
    
    # Match contract enum: "Platinum Safe", "Gold Standard", "Silver Moderate", "High Risk"
    tier_map = {
        "PLATINUM SAFE": "Platinum Safe",
        "GOLD STANDARD": "Gold Standard",
        "SILVER MODERATE": "Silver Moderate",
        "HIGH RISK": "High Risk"
    }
    actuarial_tier = tier_map.get(raw_tier, "Platinum Safe")
    discount = int(profile.get("insurance", {}).get("discount_percent", 25))
    trend = profile.get("trend", "IMPROVING")
    
    pillars_raw = profile.get("pillars", {})
    pillars_obj = PillarPct(
        smoothness_pct=int(round(pillars_raw.get("smoothness", 92.0))),
        cornering_pct=int(round(pillars_raw.get("cornering", 85.0))),
        speed_compliance_pct=int(round(pillars_raw.get("speed_compliance", 88.0))),
        vigilance_pct=int(round(pillars_raw.get("vigilance", 84.0)))
    )
    
    return DriverScoreResponse(
        overall_score=score_int,
        actuarial_tier=actuarial_tier,
        insurance_discount_pct=discount,
        trend=trend,
        pillars=pillars_obj,
        fine_tickets=FINE_TICKETS_STORE
    )

# --- 6. HEATMAP CONTRACT ENDPOINT ---
@router.get("/api/heatmap", response_model=HeatmapContractResponse)
def get_contract_heatmap():
    raw_data = risk_engine.get_heatmap_data()
    
    weighted_pts: List[WeightedPoint] = []
    for pt in raw_data.get("weighted_points", []):
        weighted_pts.append(WeightedPoint(
            lat=pt["lat"],
            lon=pt["lon"],
            weight=round(float(pt["weight"]), 2),
            location_name=pt.get("location_name", "Accident Hotspot Cluster")
        ))
        
    blackspot_zones: List[BlackspotZoneItem] = []
    for bz in raw_data.get("blackspot_zones", []):
        blackspot_zones.append(BlackspotZoneItem(
            id=bz["id"],
            name=bz["name"],
            lat=bz["lat"],
            lon=bz["lon"],
            radius_m=bz["radius_m"],
            color=bz.get("color", "#9D0208"),
            historical_crashes=bz["historical_crashes"],
            fatalities=bz["fatalities"],
            speed_limit_kmh=bz["speed_limit_kmh"]
        ))
        
    return HeatmapContractResponse(
        total_incidents=len(weighted_pts),
        center_lat=23.1124,
        center_lon=72.5489,
        weighted_points=weighted_pts,
        blackspot_zones=blackspot_zones
    )
