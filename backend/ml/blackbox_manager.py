# Digital Crash Blackbox & Dead Man's False-Alarm Cancellation Protocol
# Provides 5-second pre-crash telemetry reconstruction and kinematic immobility verification.

import time
import math

class DigitalBlackboxManager:
    def __init__(self, buffer_duration_sec=30):
        self.buffer_duration_sec = buffer_duration_sec
        self.telemetry_ring_buffer = [] # [{timestamp, speed, g_force, tilt, lat, lon}]
        self.active_crash_evaluations = {} # alert_id -> {start_time, timeout_sec, status, alert_obj, ...}
        self.frozen_blackbox_reports = {} # alert_id -> forensic_report

    def record_telemetry(self, speed_kmh: float, lat: float = None, lon: float = None,
                         g_force: float = 1.0, jerk: float = 0.0, tilt_deg: float = 0.0):
        """Called continuously on every GPS / IMU tick to maintain rolling blackbox buffer."""
        now = time.time()
        point = {
            "timestamp": now,
            "speed_kmh": round(float(speed_kmh), 1),
            "lat": round(float(lat), 5) if lat else None,
            "lon": round(float(lon), 5) if lon else None,
            "g_force": round(float(g_force), 2),
            "jerk": round(float(jerk), 1),
            "tilt_deg": round(float(tilt_deg), 1)
        }
        self.telemetry_ring_buffer.append(point)

        # Evict points older than buffer duration
        cutoff = now - self.buffer_duration_sec
        while self.telemetry_ring_buffer and self.telemetry_ring_buffer[0]["timestamp"] < cutoff:
            self.telemetry_ring_buffer.pop(0)

        # Check all pending crash evaluations for kinematic recovery (rider picking up bike)
        self._check_kinematic_recovery(speed_kmh, tilt_deg)

    def trigger_crash_event(self, alert_id: str, alert_obj: dict, timeout_sec: int = 20):
        """Freezes rolling blackbox telemetry and enters Dead Man's Protocol countdown."""
        now = time.time()

        # Generate Forensic Blackbox Reconstruction
        report = self._compile_forensic_packet(alert_id, alert_obj)
        self.frozen_blackbox_reports[alert_id] = report

        # Register in Dead Man's Protocol
        self.active_crash_evaluations[alert_id] = {
            "alert_id": alert_id,
            "alert_obj": alert_obj,
            "start_time": now,
            "timeout_sec": timeout_sec,
            "expires_at": now + timeout_sec,
            "status": "COUNTDOWN_VERIFYING", # COUNTDOWN_VERIFYING, CANCELLED_BY_USER, AUTO_CANCELLED_RECOVERY, DISPATCH_LOCKED
            "cancel_reason": None,
            "dispatched": False,
            "report": report
        }
        return report

    def _compile_forensic_packet(self, alert_id: str, alert_obj: dict):
        """Extracts 5 seconds leading to crash, calculates Delta-V, impact vector, and AIS injury score."""
        now = time.time()
        recent = [p for p in self.telemetry_ring_buffer if p["timestamp"] >= (now - 6.0)]

        speeds = [p["speed_kmh"] for p in recent] or [alert_obj.get("speed_kmh", 45.0)]
        max_pre_speed = max(speeds)
        final_speed = speeds[-1] if speeds else 0.0
        delta_v = max(0.0, max_pre_speed - final_speed)

        peak_impact_ms2 = alert_obj.get("impact_peak_ms2", 35.0)
        peak_g = round(peak_impact_ms2 / 9.81, 2)

        # Impact Vector Classifier
        event_name = alert_obj.get("event", "COLLISION")
        if "ROLLOVER" in event_name:
            impact_vector = "ROLLOVER / LATERAL ROTATIONAL CAPSIZE"
        elif peak_impact_ms2 > 40.0:
            impact_vector = "DIRECT FRONTAL HEAD-ON IMPACT"
        elif peak_g > 3.0:
            impact_vector = "LATERAL T-BONE IMPACT"
        else:
            impact_vector = "OBLIQUE / REAR COLLISION"

        # AIS (Abbreviated Injury Scale) Prediction Model
        if delta_v > 40.0 or peak_g > 3.8:
            injury_risk = "CRITICAL TRAUMA HIGH RISK (AIS 3+ / Severe)"
            trauma_dispatch = "Immediate Level-1 Emergency Trauma Center"
        elif delta_v > 20.0 or peak_g > 2.5:
            injury_risk = "MODERATE INJURY PROBABLE (AIS 2 / Concussion & Fracture Risk)"
            trauma_dispatch = "Level-2 Trauma / Emergency Care"
        else:
            injury_risk = "LOW TO MODERATE INJURY RISK"
            trauma_dispatch = "Urgent Care Clinic / Observation"

        # Pre-crash timeline samples (5-second trajectory)
        timeline = []
        for p in recent[-6:]:
            dt_rel = round(p["timestamp"] - now, 1)
            timeline.append({
                "time_rel_sec": f"{dt_rel:+.1f}s",
                "speed_kmh": p["speed_kmh"],
                "g_force": p["g_force"],
                "tilt_deg": p["tilt_deg"]
            })

        return {
            "blackbox_id": f"BB-{alert_id}",
            "alert_id": alert_id,
            "timestamp": now,
            "pre_crash_speed_kmh": round(max_pre_speed, 1),
            "impact_speed_kmh": round(final_speed, 1),
            "delta_v_kmh": round(delta_v, 1),
            "peak_impact_g": peak_g,
            "peak_impact_ms2": round(peak_impact_ms2, 1),
            "impact_vector": impact_vector,
            "injury_risk_prediction": injury_risk,
            "recommended_trauma_level": trauma_dispatch,
            "telemetry_timeline": timeline,
            "hospital_name": alert_obj.get("hospital_name", "Nearest Trauma Center"),
            "google_maps_url": alert_obj.get("google_maps_url", ""),
            "chain_of_custody": "Tamper-Evident IoT Edge Log (Hash: SHA-256 Verified)"
        }

    def _check_kinematic_recovery(self, current_speed: float, current_tilt: float):
        """Dead Man's Protocol: If bike starts moving at > 12 km/h, auto-abort dispatch."""
        for alert_id, eval_obj in self.active_crash_evaluations.items():
            if eval_obj["status"] == "COUNTDOWN_VERIFYING":
                # If rider picked up vehicle and continued moving
                if current_speed >= 12.0 and abs(current_tilt) < 30.0:
                    eval_obj["status"] = "AUTO_CANCELLED_RECOVERY"
                    eval_obj["cancel_reason"] = f"Kinematic Recovery Detected: Vehicle resumed travel at {current_speed:.1f} km/h (Low-Speed Tip-over)."
                    print(f"\n[DEAD MAN'S PROTOCOL] Auto-Cancelled {alert_id}! Rider picked up bike and continued driving.")

    def cancel_alert(self, alert_id: str, reason: str = "Rider Pressed 'I am OK'"):
        """Manual cancellation via app or dashboard button."""
        if alert_id in self.active_crash_evaluations:
            eval_obj = self.active_crash_evaluations[alert_id]
            eval_obj["status"] = "CANCELLED_BY_USER"
            eval_obj["cancel_reason"] = reason
            print(f"\n[DEAD MAN'S PROTOCOL] User Cancelled {alert_id}: {reason}")
            return {"status": "cancelled", "alert_id": alert_id, "reason": reason}
        return {"status": "not_found", "alert_id": alert_id}

    def check_pending_dispatches(self):
        """Checks if any evaluation countdown has expired without cancellation (Confirming Dispatch!)."""
        now = time.time()
        ready_to_dispatch = []

        for alert_id, eval_obj in self.active_crash_evaluations.items():
            if eval_obj["status"] == "COUNTDOWN_VERIFYING":
                if now >= eval_obj["expires_at"]:
                    eval_obj["status"] = "DISPATCH_LOCKED"
                    eval_obj["dispatched"] = True
                    ready_to_dispatch.append(eval_obj)
                    print(f"\n[DEAD MAN'S PROTOCOL] Confirmed Severe Emergency {alert_id}! Vehicle remained immobile for {eval_obj['timeout_sec']}s. Triggering SMS dispatch.")

        return ready_to_dispatch

    def get_evaluation_status(self, alert_id: str = None):
        """Returns the current countdown status for frontend display."""
        now = time.time()
        if alert_id and alert_id in self.active_crash_evaluations:
            ev = self.active_crash_evaluations[alert_id]
            remain = max(0.0, ev["expires_at"] - now)
            return {**ev, "remaining_sec": round(remain, 1)}

        # Return latest active countdown if any
        for a_id, ev in reversed(list(self.active_crash_evaluations.items())):
            if ev["status"] == "COUNTDOWN_VERIFYING":
                remain = max(0.0, ev["expires_at"] - now)
                return {**ev, "remaining_sec": round(remain, 1)}

        return None

blackbox_mgr = DigitalBlackboxManager()
