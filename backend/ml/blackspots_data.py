# Accident Blackspots & High-Risk Road Segments Registry
# Focus: Gujarat State Highway & National Highway Corridors

BLACKSPOTS = [
    {
        "id": "BS_001",
        "name": "SG Highway - Iskcon Crossroad Overpass",
        "lat": 23.0298,
        "lon": 72.5074,
        "radius_m": 180,
        "hazard_type": "HIGHWAY_INTERSECTION",
        "speed_limit_kmh": 50,
        "historical_crashes": 42,
        "fatalities": 8,
        "severity_weight": 2.8,
        "description": "High-speed merging traffic with sudden queuing on overpass ramp."
    },
    {
        "id": "BS_002",
        "name": "Vaishno Devi Circle - Ring Road Merge",
        "lat": 23.1368,
        "lon": 72.5448,
        "radius_m": 220,
        "hazard_type": "ROTARY_ROUNDABOUT_MERGE",
        "speed_limit_kmh": 40,
        "historical_crashes": 36,
        "fatalities": 5,
        "severity_weight": 2.5,
        "description": "Multi-lane roundabout with high commercial truck conflicts."
    },
    {
        "id": "BS_003",
        "name": "SG Highway - Pakwan Junction",
        "lat": 23.0425,
        "lon": 72.5186,
        "radius_m": 150,
        "hazard_type": "BLIND_CURVE_AND_SIGNAL",
        "speed_limit_kmh": 50,
        "historical_crashes": 29,
        "fatalities": 4,
        "severity_weight": 2.2,
        "description": "Frequent red-light violations and pedestrian crossing conflicts."
    },
    {
        "id": "BS_004",
        "name": "Mehsana - Ahmedabad Highway SH-41 - Chhatral GIDC Curve",
        "lat": 23.3280,
        "lon": 72.4350,
        "radius_m": 250,
        "hazard_type": "SHARP_INDUSTRIAL_CURVE",
        "speed_limit_kmh": 60,
        "historical_crashes": 51,
        "fatalities": 14,
        "severity_weight": 3.0,
        "description": "Sharp reverse S-curve with heavy chemical and container trailers."
    },
    {
        "id": "BS_005",
        "name": "Mehsana Bypass - Modhera Crossroad",
        "lat": 23.5780,
        "lon": 72.3680,
        "radius_m": 200,
        "hazard_type": "UNSIGNALIZED_JUNCTION",
        "speed_limit_kmh": 40,
        "historical_crashes": 33,
        "fatalities": 6,
        "severity_weight": 2.4,
        "description": "Poor nighttime illumination and high tractor crossing."
    },
    {
        "id": "BS_006",
        "name": "Civil Hospital Mehsana Approach - Radhanpur Road",
        "lat": 23.5930,
        "lon": 72.3850,
        "radius_m": 140,
        "hazard_type": "AMBULANCE_EMERGENCY_CORRIDOR",
        "speed_limit_kmh": 35,
        "historical_crashes": 18,
        "fatalities": 2,
        "severity_weight": 1.8,
        "description": "Dense ambulance ingress, pedestrian movement, and sudden stopping."
    },
    {
        "id": "BS_007",
        "name": "Kalupur Railway Station Overbridge Approach",
        "lat": 23.0270,
        "lon": 72.6010,
        "radius_m": 160,
        "hazard_type": "DENSE_URBAN_BOTTLENECK",
        "speed_limit_kmh": 30,
        "historical_crashes": 22,
        "fatalities": 1,
        "severity_weight": 1.9,
        "description": "Narrow elevated bridge with heavy two-wheeler and auto density."
    },
    {
        "id": "BS_008",
        "name": "Gujarat University / Helmet Crossroad",
        "lat": 23.0450,
        "lon": 72.5350,
        "radius_m": 170,
        "hazard_type": "STUDENT_PEDESTRIAN_ZONE",
        "speed_limit_kmh": 40,
        "historical_crashes": 27,
        "fatalities": 3,
        "severity_weight": 2.0,
        "description": "High student pedestrian crossing and sudden bus lane merges."
    },
    {
        "id": "BS_009",
        "name": "Gita Mandir - ST Bus Terminal Corridor",
        "lat": 23.0125,
        "lon": 72.5890,
        "radius_m": 190,
        "hazard_type": "BUS_TERMINAL_CONFLICT_ZONE",
        "speed_limit_kmh": 35,
        "historical_crashes": 31,
        "fatalities": 5,
        "severity_weight": 2.3,
        "description": "Continuous intercity heavy bus blind spots."
    }
]

def get_all_blackspots():
    return BLACKSPOTS
