# Industrial-Grade 4-Pillar Driver Safety Telematics Engine
# Evaluates longitudinal dynamics, lateral stability, speed compliance, and hazard vigilance.
# Conforms to commercial telematics insurer standards (Root / Progressive / Zendrive).

import time
from typing import Dict, Any, List

class DriverSafetyScorer:
    def __init__(self):
        # 4 Core Telematics Pillars (0.0 to 100.0)
        self.smoothness_score = 100.0        # Longitudinal braking & acceleration dynamics
        self.cornering_score = 100.0         # Lateral dynamics, swerve & chassis roll
        self.speed_compliance_score = 100.0  # Adherence to road segment speed limits
        self.vigilance_score = 100.0         # Road defect & accident blackspot caution

        self.last_recovery_time = time.time()
        self.last_event_time = time.time()
        self.score_history = [100.0]

        self.counts = {
            "HARSH_BRAKING": 0,
            "AGGRESSIVE_CORNERING": 0,
            "HARSH_ACCELERATION": 0,
            "OVERSPEEDING": 0,
            "POTHOLE_IMPACT": 0
        }

        self.penalty_log = []

    @property
    def score(self) -> float:
        """
        Composite Driver Safety Index (DSI) weighted across 4 validated pillars:
        - Smoothness (35%)
        - Cornering (25%)
        - Speed Compliance (25%)
        - Vigilance (15%)
        """
        dsi = (
            0.35 * self.smoothness_score +
            0.25 * self.cornering_score +
            0.25 * self.speed_compliance_score +
            0.15 * self.vigilance_score
        )
        return float(round(max(10.0, min(100.0, dsi)), 1))

    def _apply_natural_recovery(self):
        """
        Defensive Driving Reward: Clean, smooth telemetry restores all 4 pillars
        gradually toward 100.0 (+1.2 points per 15 seconds without harsh events).
        """
        now = time.time()
        elapsed = now - self.last_recovery_time
        if elapsed >= 15.0:
            quiet_time = now - self.last_event_time
            if quiet_time > 10.0:
                steps = int(elapsed / 15.0)
                boost = steps * 1.25

                self.smoothness_score = min(100.0, self.smoothness_score + boost)
                self.cornering_score = min(100.0, self.cornering_score + boost)
                self.speed_compliance_score = min(100.0, self.speed_compliance_score + (boost * 0.8))
                self.vigilance_score = min(100.0, self.vigilance_score + boost)

                self.score_history.append(self.score)
                if len(self.score_history) > 30:
                    self.score_history.pop(0)

            self.last_recovery_time = now

    def register_event(self, event_type: str, severity: float = 1.0, details: str = ""):
        """
        Applies point deductions targeting the specific physics pillar affected.
        """
        self._apply_natural_recovery()
        now = time.time()
        self.last_event_time = now
        self.last_recovery_time = now

        deduction = 0.0
        pillar_affected = ""
        reason = ""

        evt = event_type.upper()

        if "BRAKING" in evt:
            # Longitudinal deceleration shock -> Smoothness pillar
            deduction = 7.5 * max(0.7, severity)
            self.smoothness_score = max(10.0, self.smoothness_score - deduction)
            self.counts["HARSH_BRAKING"] += 1
            pillar_affected = "Smoothness & Braking"
            reason = "Sudden longitudinal deceleration shock"

        elif "ACCELERATION" in evt:
            # Longitudinal acceleration surge -> Smoothness pillar
            deduction = 5.0 * max(0.7, severity)
            self.smoothness_score = max(15.0, self.smoothness_score - deduction)
            self.counts["HARSH_ACCELERATION"] += 1
            pillar_affected = "Smoothness & Braking"
            reason = "Rapid longitudinal acceleration surge"

        elif "CORNERING" in evt or "ROLLOVER" in evt:
            # Lateral swerve / tilt -> Cornering pillar
            deduction = 9.0 * max(0.7, severity)
            self.cornering_score = max(10.0, self.cornering_score - deduction)
            self.counts["AGGRESSIVE_CORNERING"] += 1
            pillar_affected = "Cornering & Roll Stability"
            reason = "High lateral g-force swerve or chassis tilt"

        elif "POTHOLE" in evt:
            # Vertical shock impact -> Vigilance pillar
            deduction = 6.0 * max(0.6, severity)
            self.vigilance_score = max(15.0, self.vigilance_score - deduction)
            self.counts["POTHOLE_IMPACT"] += 1
            pillar_affected = "Hazard Vigilance"
            reason = "High-velocity road pothole impact"

        elif "OVERSPEED" in evt:
            # Speed violation -> Speed Compliance pillar
            deduction = 10.0 * max(0.8, severity)
            self.speed_compliance_score = max(10.0, self.speed_compliance_score - deduction)
            self.counts["OVERSPEEDING"] += 1
            pillar_affected = "Speed Compliance"
            reason = "Vehicle velocity exceeded zone limit"

        if deduction > 0:
            entry = {
                "timestamp": now,
                "event": event_type,
                "pillar": pillar_affected,
                "deduction": round(deduction, 1),
                "composite_score_after": self.score,
                "reason": reason,
                "details": details
            }
            self.penalty_log.insert(0, entry)
            if len(self.penalty_log) > 40:
                self.penalty_log.pop()

            self.score_history.append(self.score)
            if len(self.score_history) > 30:
                self.score_history.pop(0)

    def register_speed_telemetry(self, current_speed_kmh: float, speed_limit_kmh: float):
        """
        Continuous speed compliance scoring.
        Rewards driving within limits, penalizes sustained speeding.
        """
        self._apply_natural_recovery()
        if current_speed_kmh <= 0.5:
            return

        excess = current_speed_kmh - speed_limit_kmh
        if excess > 5.0:
            # Penalize speed compliance pillar proportional to excess speed
            severity = min(2.5, excess / 15.0)
            penalty = 1.5 * severity
            self.speed_compliance_score = max(10.0, round(self.speed_compliance_score - penalty, 1))
            self.register_event(
                "OVERSPEEDING",
                severity=severity,
                details=f"{current_speed_kmh:.1f} km/h (Limit: {speed_limit_kmh:.0f} km/h)"
            )
        else:
            # Mild continuous compliance boost
            self.speed_compliance_score = min(100.0, self.speed_compliance_score + 0.3)

    def get_trend(self) -> str:
        """Determines score trajectory: IMPROVING, STABLE, or DECLINING."""
        if len(self.score_history) < 2:
            return "STABLE"
        delta = self.score_history[-1] - self.score_history[0]
        if delta > 1.5:
            return "IMPROVING"
        elif delta < -1.5:
            return "DECLINING"
        return "STABLE"

    def get_profile(self) -> Dict[str, Any]:
        """
        Returns complete, structured telematics report for Android client and web dashboard.
        """
        self._apply_natural_recovery()
        dsi = self.score

        # Driver Tier Classification
        if dsi >= 90.0:
            tier = "PLATINUM SAFE"
            profile = "EXCELLENT"
            description = "Exceptional anticipation, ultra-smooth braking, and perfect speed adherence."
            badge_color = "success"
            insurance_discount_pct = 25
            insurance_status = "Eligible for 25% Premium Cash-back Discount"
        elif dsi >= 80.0:
            tier = "GOLD CAUTIOUS"
            profile = "GOOD"
            description = "Defensive driving with rare harsh deceleration shocks."
            badge_color = "info"
            insurance_discount_pct = 15
            insurance_status = "Eligible for 15% Safe Driver Discount"
        elif dsi >= 68.0:
            tier = "SILVER COMMUTER"
            profile = "MODERATE"
            description = "Standard driving dynamics with occasional rapid accelerations."
            badge_color = "warning"
            insurance_discount_pct = 5
            insurance_status = "Standard Commercial Coverage"
        elif dsi >= 50.0:
            tier = "BRONZE HIGH ALERT"
            profile = "AGGRESSIVE"
            description = "Elevated collision probability. Frequent abrupt braking and cornering swerves."
            badge_color = "danger"
            insurance_discount_pct = 0
            insurance_status = "High-Risk Tier: Underwriter Coaching Required"
        else:
            tier = "CRITICAL RECKLESS"
            profile = "RECKLESS"
            description = "Critical accident risk. Repeated severe infractions logged."
            badge_color = "dark"
            insurance_discount_pct = 0
            insurance_status = "Critical Risk Surcharge (+25%)"

        # Context-aware intelligent driving tip based on lowest pillar
        pillars = {
            "Smoothness": round(self.smoothness_score, 1),
            "Cornering": round(self.cornering_score, 1),
            "Speed Compliance": round(self.speed_compliance_score, 1),
            "Vigilance": round(self.vigilance_score, 1)
        }
        lowest_pillar = min(pillars, key=pillars.get)

        if lowest_pillar == "Smoothness":
            tip = "Maintain a 3-second following gap to avoid emergency braking shocks."
        elif lowest_pillar == "Cornering":
            tip = "Ease off throttle before steering into curves to reduce vehicle lateral roll."
        elif lowest_pillar == "Speed Compliance":
            tip = "Observe posted speed limits, especially near intersections and crosswalks."
        else:
            tip = "Slow down over degraded road segments to protect vehicle chassis and control."

        return {
            "score": dsi,
            "tier": tier,
            "profile": profile,
            "badge_color": badge_color,
            "description": description,
            "tip": tip,
            "trend": self.get_trend(),
            "insurance": {
                "discount_percent": insurance_discount_pct,
                "status": insurance_status
            },
            "pillars": {
                "smoothness": round(self.smoothness_score, 1),
                "cornering": round(self.cornering_score, 1),
                "speed_compliance": round(self.speed_compliance_score, 1),
                "vigilance": round(self.vigilance_score, 1)
            },
            "counts": self.counts,
            "recent_penalties": self.penalty_log[:5]
        }

# Global singleton instance for vehicle tracking
driver_scorer = DriverSafetyScorer()
