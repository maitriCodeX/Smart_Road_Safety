# Smart Road Safety - AI Telematics Backend Core

FastAPI telematics server, 4-pillar driver safety engine, Gaussian risk heatmap, edge crash detector with 20-second Dead Man's Switch, and Android app integration contracts.

---

## 🚀 Quickstart

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Launch the Backend Server
```bash
python main.py
```
* Server runs on `http://0.0.0.0:8000`
* Live Web Command Center & Monitoring: `http://localhost:8000/`
* Interactive API Documentation (Swagger): `http://localhost:8000/docs`

### 3. Expose via Public Tunnel (For External Android Testing)
```powershell
powershell -ExecutionPolicy Bypass -File .\keep_tunnel.ps1
```
Or directly:
```bash
npx -y localtunnel --port 8000
```
*(Note: When calling via localtunnel, include header `Bypass-Tunnel-Reminder: true`)*

---

## 📂 Architecture Overview
* `main.py`: FastAPI server, GPS stream routing (`VH001` vs simulation), Dead Man's Switch 20s SOS dispatch, Leaflet dashboard, and SSE telemetry stream.
* `android_contract.py`: Full implementation of all frontend teammate schemas (Auth, User Profile, Navigation, Frequent Routes, Driver Score with Fine Tickets, Heatmap).
* `ml/`:
  * `safety_scorer.py`: 4-Pillar Telematics Engine (Smoothness 35%, Cornering 25%, Speed Compliance 25%, Vigilance 15%) + UBI insurance tiers.
  * `risk_engine.py`: High-density 132-point Gaussian thermal risk mesh & geofenced blackspots.
  * `impact_detector.py`: 3-axis IMU jerk vector calculation ($\Delta a / \Delta t$) and crash detection.
  * `pothole_tracker.py`: Road Quality Index (RQI) and municipal defect logging.
  * `blackspots_data.py`: High-fatality accident corridor registry (Gujarat highways).
  * `blackbox_manager.py`: Forensic crash data recorder with 20-second Dead Man's Protocol.
* `clients/`:
  * `ANDROID_ENDPOINTS_CHEATSHEET.md`: Quick reference list of all endpoints, parameters, and paths.
  * `ANDROID_INTEGRATION_GUIDE.md`: Kotlin code snippets for Google Maps `HeatmapTileProvider`, Retrofit, and OkHttp SSE.
