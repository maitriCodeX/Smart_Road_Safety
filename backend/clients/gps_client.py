import time
import requests

# Set this to your teammate running the backend (e.g. "http://10.32.186.140:8000" or "http://localhost:8000")
BACKEND_HOST = "http://10.32.186.140:8000"
GPS_ENDPOINT = f"{BACKEND_HOST}/api/gps"
DEVICE_ID = "VH001"

def push_gps_to_backend(latitude: float, longitude: float, speed_kmh: float = 0.0, heading_deg: float = 0.0):
    """
    Call this function whenever your phone GPS receiver gets a new location update.
    """
    payload = {
        "device_id": DEVICE_ID,
        "latitude": latitude,
        "longitude": longitude,
        "speed_kmh": speed_kmh,
        "heading_deg": heading_deg,
        "timestamp": time.time()
    }
    try:
        res = requests.post(GPS_ENDPOINT, json=payload, timeout=2)
        if res.status_code == 200:
            print(f"[GPS OK] Sent: ({latitude:.5f}, {longitude:.5f}) | Speed: {speed_kmh:.1f} km/h")
            return True
        else:
            print(f"[GPS ERR] Server returned status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"[GPS ERR] Failed to reach backend: {e}")
    return False

if __name__ == "__main__":
    print("=== GPS PHONE CLIENT (Testing Mode) ===")
    print(f"Target Backend: {GPS_ENDPOINT}")
    print("Streaming simulated driving route near SG Highway...")

    # Simulated drive coordinates
    route_points = [
        (23.0225, 72.5714, 45.0, 90.0),
        (23.0230, 72.5725, 48.0, 92.0),
        (23.0238, 72.5739, 52.0, 95.0),
        (23.0245, 72.5750, 42.0, 90.0),
        (23.0252, 72.5762, 35.0, 88.0),
    ]

    for lat, lon, spd, head in route_points:
        push_gps_to_backend(lat, lon, spd, head)
        time.sleep(2)
