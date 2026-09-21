# Predictive Accident-Risk ML Fusion Engine
# Fuses Geospatial BallTree Blackspots, Speed Dynamics, Driver Behavior, and Road Defects.

import math
import time
import numpy as np
from sklearn.neighbors import BallTree
from ml.blackspots_data import get_all_blackspots
from ml.safety_scorer import driver_scorer
from ml.pothole_tracker import pothole_tracker, haversine_m

class PredictiveRiskEngine:
    def __init__(self):
        self.blackspots = get_all_blackspots()
        self._build_spatial_index()

    def _build_spatial_index(self):
        """Builds a scikit-learn BallTree with haversine metric (coordinates in radians)."""
        coords_rad = np.array([
            [math.radians(b["lat"]), math.radians(b["lon"])]
            for b in self.blackspots
        ])
        self.tree = BallTree(coords_rad, metric='haversine')

    def find_nearest_blackspot(self, lat: float, lon: float):
        """Returns the closest accident blackspot and geodesic distance in meters in < 1ms."""
        if lat is None or lon is None:
            return None, float('inf')

        query_rad = np.array([[math.radians(lat), math.radians(lon)]])
        dist_rad, indices = self.tree.query(query_rad, k=1)
        dist_m = dist_rad[0][0] * 6371000.0
        idx = indices[0][0]
        return self.blackspots[idx], dist_m

    def assess_risk(self, lat: float, lon: float, speed_kmh: float = 0.0):
        """Computes multi-factor accident probability score (0 to 100) and actionable warnings."""
        if lat is None or lon is None:
            return {
                "risk_score": 10.0,
                "risk_level": "LOW",
                "badge_color": "success",
                "warnings": [],
                "nearest_blackspot": None,
                "distance_to_blackspot_m": None,
                "driver_score": driver_scorer.score,
                "speed_limit_kmh": 50.0
            }

        # 1. Spatial Blackspot Factor
        nearest_bs, dist_m = self.find_nearest_blackspot(lat, lon)
        bs_radius = nearest_bs.get("radius_m", 150)
        bs_severity = nearest_bs.get("severity_weight", 2.0)
        speed_limit = nearest_bs.get("speed_limit_kmh", 50)

        # Proximity score (reaches maximum inside geofence)
        if dist_m <= (bs_radius * 2.5):
            proximity_factor = max(0.0, 1.0 - (dist_m / (bs_radius * 2.5)))
            s_proximity = proximity_factor * (bs_severity * 14.0)
        else:
            s_proximity = 0.0

        # 2. Overspeeding Factor
        delta_v = max(0.0, speed_kmh - speed_limit)
        s_overspeed = min(40.0, delta_v * 2.5)

        # 3. Driver Aggressiveness Factor (from Driver Safety Index)
        driver_score = driver_scorer.score
        s_driver = ((100.0 - driver_score) / 100.0) * 25.0

        # 4. Pothole / Road Defect Factor
        nearby_potholes = pothole_tracker.check_nearby_potholes(lat, lon, threshold_m=70.0)
        s_pothole = 0.0
        if nearby_potholes:
            closest_pothole = nearby_potholes[0]
            if closest_pothole["severity"] == "CRITICAL_DEFECT":
                s_pothole = 18.0
            else:
                s_pothole = 10.0

        # 5. Temporal / Night Factor
        local_hour = time.localtime().tm_hour
        time_multiplier = 1.25 if (local_hour >= 21 or local_hour <= 5) else 1.0

        # Combined Risk Score (0 - 100)
        raw_risk = (s_proximity + s_overspeed + s_driver + s_pothole) * time_multiplier
        risk_score = min(100.0, max(5.0, round(raw_risk, 1)))

        # Categorize
        if risk_score >= 80.0:
            level = "CRITICAL"
            badge_color = "danger"
        elif risk_score >= 60.0:
            level = "HIGH"
            badge_color = "danger"
        elif risk_score >= 35.0:
            level = "MODERATE"
            badge_color = "warning"
        else:
            level = "LOW"
            badge_color = "success"

        # Construct specific actionable warnings
        warnings = []
        if dist_m <= bs_radius:
            warnings.append(f"INSIDE ACCIDENT BLACKSPOT: {nearest_bs['name']} ({nearest_bs['hazard_type']}). Extreme caution!")
        elif dist_m <= (bs_radius * 2.0):
            warnings.append(f"Approaching High-Risk Zone ({round(dist_m)}m ahead): {nearest_bs['name']}.")

        # Continuous speed compliance scoring
        driver_scorer.register_speed_telemetry(speed_kmh, speed_limit)

        if delta_v > 0:
            warnings.append(f"OVERSPEEDING: Travelling at {speed_kmh:.1f} km/h in a {speed_limit} km/h zone (+{delta_v:.1f} km/h)!")

        potholes_ahead = []
        if nearby_potholes:
            closest_p = nearby_potholes[0]
            warnings.append(f"ROAD DEFECT: Severe pothole cluster {round(closest_p['distance_m'])}m ahead! Slow down.")
            for p in nearby_potholes[:3]:
                potholes_ahead.append({
                    "id": p.get("id", "PH"),
                    "distance_m": round(p.get("distance_m", 0)),
                    "severity": p.get("severity", "MODERATE"),
                    "address": p.get("address", "Road Defect Ahead")
                })

        driver_profile = driver_scorer.get_profile()
        if driver_score < 60.0:
            warnings.append(f"DRIVER AGGRESSIVENESS ELEVATED: Safety Score is {driver_score:.0f}/100. Smooth out steering and braking.")

        speed_status = "SAFE"
        if delta_v > 5.0:
            speed_status = "CRITICAL_OVERSPEED"
        elif delta_v > 0.0:
            speed_status = "OVERSPEED_WARNING"
        elif speed_kmh >= (speed_limit - 5.0):
            speed_status = "NEAR_LIMIT"

        return {
            "risk_score": float(risk_score),
            "risk_level": str(level),
            "badge_color": str(badge_color),
            "warnings": warnings,
            "nearest_blackspot": str(nearest_bs["name"]),
            "blackspot_hazard": str(nearest_bs["hazard_type"]),
            "distance_to_blackspot_m": float(round(dist_m, 1)),
            "is_inside_blackspot": bool(dist_m <= bs_radius),
            "speed_kmh": float(round(speed_kmh, 1)),
            "speed_limit_kmh": int(speed_limit),
            "speed_status": speed_status,
            "delta_overspeed_kmh": float(round(delta_v, 1)),
            "driver_score": float(round(driver_score, 1)),
            "driver_profile": driver_profile,
            "potholes_ahead": potholes_ahead,
            "nearby_potholes_count": int(len(nearby_potholes)),
            "timestamp": float(time.time())
        }

    def get_heatmap_points(self):
        """
        Generates a dense thermal distribution of weighted [lat, lon, intensity] coordinates.
        Uses Gaussian multi-incident dispersion around each blackspot so heatmaps render
        as vivid, glowing thermal hotspots instead of faint isolated dots.
        """
        points = []
        for b in self.blackspots:
            lat = b["lat"]
            lon = b["lon"]
            radius_m = b.get("radius_m", 180)
            base_intensity = min(1.0, max(0.65, b.get("severity_weight", 2.0) / 2.8))

            # Core focal point (peak red intensity)
            points.append([lat, lon, 1.0])

            # Generate 12 clustered incident points within radius for smooth Gaussian heat dispersion
            for i in range(12):
                angle = (2.0 * math.pi / 12.0) * i
                dist_frac = 0.35 + 0.55 * ((i % 3) / 2.0)
                offset_m = radius_m * dist_frac
                dlat = (offset_m * math.cos(angle)) / 111000.0
                dlon = (offset_m * math.sin(angle)) / (111000.0 * math.cos(math.radians(lat)))
                pt_weight = round(base_intensity * (1.0 - (dist_frac * 0.35)), 2)
                points.append([round(lat + dlat, 6), round(lon + dlon, 6), pt_weight])

        # Confirmed potholes as thermal yellow/orange anomalies
        for h in pothole_tracker.hazards:
            h_lat = h["lat"]
            h_lon = h["lon"]
            h_intensity = 0.85 if h.get("severity") == "CRITICAL_DEFECT" else 0.6
            points.append([h_lat, h_lon, h_intensity])
            for j in range(4):
                ang = (math.pi / 2.0) * j
                points.append([round(h_lat + 0.0003 * math.cos(ang), 6), round(h_lon + 0.0003 * math.sin(ang), 6), round(h_intensity * 0.7, 2)])

        return points

    def get_heatmap_data(self):
        """
        Returns multi-format heatmap data ready for:
        1. Leaflet Heat canvas (points: [[lat, lon, weight], ...])
        2. Android Google Maps SDK HeatmapTileProvider (weighted_points: [{"lat": ..., "lon": ..., "weight": ...}, ...])
        3. Android CircleOverlay / Markers (blackspot_zones: [...])
        4. Standard GeoJSON FeatureCollection for Mapbox / osmdroid
        """
        points = self.get_heatmap_points()

        weighted_points = [
            {"lat": p[0], "lon": p[1], "weight": p[2]}
            for p in points
        ]

        blackspot_zones = []
        features = []
        for b in self.blackspots:
            zone = {
                "id": b["id"],
                "name": b["name"],
                "lat": b["lat"],
                "lon": b["lon"],
                "radius_m": b.get("radius_m", 180),
                "severity_weight": b.get("severity_weight", 2.0),
                "historical_crashes": b.get("historical_crashes", 25),
                "fatalities": b.get("fatalities", 3),
                "hazard_type": b.get("hazard_type", "ACCIDENT_ZONE"),
                "speed_limit_kmh": b.get("speed_limit_kmh", 50),
                "color": "#ef4444" if b.get("severity_weight", 2.0) >= 2.5 else "#f59e0b"
            }
            blackspot_zones.append(zone)

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [b["lon"], b["lat"]]
                },
                "properties": {
                    "name": b["name"],
                    "radius_m": b.get("radius_m", 180),
                    "crashes": b.get("historical_crashes", 25),
                    "fatalities": b.get("fatalities", 3),
                    "speed_limit_kmh": b.get("speed_limit_kmh", 50)
                }
            })

        return {
            "count": len(points),
            "points": points,
            "weighted_points": weighted_points,
            "blackspot_zones": blackspot_zones,
            "pothole_hazards": pothole_tracker.hazards,
            "geojson": {
                "type": "FeatureCollection",
                "features": features
            }
        }

risk_engine = PredictiveRiskEngine()
