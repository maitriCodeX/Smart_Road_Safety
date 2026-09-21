# Autonomous Road Quality & Pothole Infrastructure Mapping (Civic ITS)
# Clusters vertical shock events from ESP32 to map road defects and compute Road Quality Index (RQI).

import math
import time

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000.0 # meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0)**2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class PotholeHazardTracker:
    def __init__(self):
        # Pre-seed realistic road defects along test corridors
        self.hazards = [
            {
                "id": "PH_001",
                "lat": 23.0315,
                "lon": 72.5090,
                "hit_count": 5,
                "peak_jerk": 420.0,
                "peak_g": 2.8,
                "severity": "SEVERE",
                "address": "SG Highway Service Road (Opp. Iscon)",
                "status": "CONFIRMED_HAZARD",
                "last_hit": time.time() - 3600
            },
            {
                "id": "PH_002",
                "lat": 23.0440,
                "lon": 72.5200,
                "hit_count": 3,
                "peak_jerk": 340.0,
                "peak_g": 2.2,
                "severity": "MODERATE",
                "address": "Pakwan Junction Flyover Ramp",
                "status": "CONFIRMED_HAZARD",
                "last_hit": time.time() - 7200
            },
            {
                "id": "PH_003",
                "lat": 23.5820,
                "lon": 72.3710,
                "hit_count": 8,
                "peak_jerk": 510.0,
                "peak_g": 3.4,
                "severity": "CRITICAL_DEFECT",
                "address": "Mehsana Bypass Heavy Vehicle Lane",
                "status": "MUNICIPAL_REPAIR_ALERT",
                "last_hit": time.time() - 1800
            }
        ]

    def register_pothole(self, lat: float, lon: float, peak_jerk: float = 350.0, peak_g: float = 2.4, address: str = ""):
        """Clusters or adds a new pothole detection."""
        if lat is None or lon is None:
            return None

        # Check if near an existing hazard (within 35 meters)
        now = time.time()
        for h in self.hazards:
            dist = haversine_m(lat, lon, h["lat"], h["lon"])
            if dist <= 35.0:
                h["hit_count"] += 1
                h["peak_jerk"] = max(h["peak_jerk"], round(peak_jerk, 1))
                h["peak_g"] = max(h["peak_g"], round(peak_g, 2))
                h["last_hit"] = now
                if h["hit_count"] >= 3:
                    h["status"] = "CONFIRMED_HAZARD"
                if h["peak_jerk"] > 450.0 or h["hit_count"] >= 6:
                    h["severity"] = "CRITICAL_DEFECT"
                return h

        # Create new unconfirmed hazard
        new_id = f"PH_{len(self.hazards) + 1:03d}"
        new_hazard = {
            "id": new_id,
            "lat": round(lat, 5),
            "lon": round(lon, 5),
            "hit_count": 1,
            "peak_jerk": round(peak_jerk, 1),
            "peak_g": round(peak_g, 2),
            "severity": "MODERATE" if peak_jerk > 320 else "LOW",
            "address": address or f"Road Segment ({lat:.4f}, {lon:.4f})",
            "status": "UNVERIFIED",
            "last_hit": now
        }
        self.hazards.append(new_hazard)
        return new_hazard

    def check_nearby_potholes(self, lat: float, lon: float, threshold_m: float = 80.0):
        """Returns list of hazardous potholes within threshold meters of vehicle."""
        if lat is None or lon is None:
            return []
        nearby = []
        for h in self.hazards:
            dist = haversine_m(lat, lon, h["lat"], h["lon"])
            if dist <= threshold_m:
                nearby.append({
                    **h,
                    "distance_m": round(dist, 1)
                })
        nearby.sort(key=lambda x: x["distance_m"])
        return nearby

    def get_road_quality_index(self):
        """Computes municipal Road Quality Index (RQI) based on active potholes."""
        total = len(self.hazards)
        critical = sum(1 for h in self.hazards if h["severity"] == "CRITICAL_DEFECT")
        confirmed = sum(1 for h in self.hazards if h["status"] in ["CONFIRMED_HAZARD", "MUNICIPAL_REPAIR_ALERT"])

        if critical >= 3 or total >= 10:
            grade = "Grade D (Poor Infrastructure - High Hazard)"
            color = "danger"
        elif confirmed >= 4:
            grade = "Grade C (Substandard - Moderate Hazard)"
            color = "warning"
        elif confirmed >= 1:
            grade = "Grade B (Fair - Isolated Defects)"
            color = "info"
        else:
            grade = "Grade A (Optimal Smooth Highway)"
            color = "success"

        return {
            "total_hazards_logged": total,
            "confirmed_potholes": confirmed,
            "critical_defects": critical,
            "road_quality_grade": grade,
            "badge_color": color,
            "hazards": self.hazards
        }

pothole_tracker = PotholeHazardTracker()
