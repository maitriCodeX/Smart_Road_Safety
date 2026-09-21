import sys
import time
import requests

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# If running on the same laptop as backend, use 127.0.0.1.
# If your friend runs this on their laptop, they pass: python messaging_worker.py http://10.32.186.140:8000
BACKEND_HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
ALERTS_ENDPOINT = f"{BACKEND_HOST}/api/emergency/alerts"

def send_hospital_emergency_sms(hospital_phone: str, hospital_name: str, message: str):
    """
    HOOK YOUR SMS / WHATSAPP / TWILIO DISPATCH HERE:
    e.g., Twilio client.messages.create(...), Fast2SMS, or GSM module
    """
    print(f"\n>> [SMS SENT TO HOSPITAL] -> {hospital_name} ({hospital_phone})", flush=True)
    print(f"   Message:\n{message}", flush=True)

def send_relative_emergency_sms(relative_phone: str, relative_name: str, message: str):
    """
    HOOK YOUR SMS / CALL / WHATSAPP DISPATCH TO FAMILY HERE:
    """
    print(f"\n>> [SMS/CALL SENT TO FAMILY] -> {relative_name} ({relative_phone})", flush=True)
    print(f"   Message:\n{message}", flush=True)

def acknowledge_alert(alert_id: str):
    try:
        ack_url = f"{ALERTS_ENDPOINT}/{alert_id}/acknowledge"
        requests.post(ack_url, timeout=2)
        print(f"[OK] Alert {alert_id} acknowledged on backend.\n", flush=True)
    except Exception as e:
        print(f"Failed to acknowledge alert {alert_id}: {e}", flush=True)

def run_messaging_worker():
    print("==================================================", flush=True)
    print(" EMERGENCY MESSAGING DISPATCH WORKER", flush=True)
    print(f" Monitoring Backend: {ALERTS_ENDPOINT}", flush=True)
    print(" Waiting for crash / emergency collision events...", flush=True)
    print("==================================================", flush=True)

    while True:
        try:
            res = requests.get(ALERTS_ENDPOINT, timeout=3)
            if res.status_code == 200:
                data = res.json()
                alerts = data.get("alerts", [])
                
                for alert in alerts:
                    if alert.get("status") == "PENDING_DISPATCH":
                        alert_id = alert["alert_id"]
                        print(f"\n[!] CRITICAL COLLISION ALERT: {alert_id}", flush=True)
                        print(f"    Vehicle: {alert['device_id']} | Impact: {alert['impact_peak_ms2']:.1f} m/s2", flush=True)
                        
                        hospital = alert["nearest_hospital"]
                        relative = alert["relative_contact"]
                        sms_body = alert["prepared_sms_text"]

                        # 1. Send Emergency alert to the nearest Hospital / Trauma Center
                        send_hospital_emergency_sms(
                            hospital_phone=hospital["phone"],
                            hospital_name=hospital["name"],
                            message=sms_body
                        )

                        # 2. Send Emergency alert to Relative / Emergency contact
                        send_relative_emergency_sms(
                            relative_phone=relative["phone"],
                            relative_name=relative["name"],
                            message=sms_body
                        )

                        # 3. Mark alert as dispatched on the backend
                        acknowledge_alert(alert_id)

        except Exception as e:
            print(f"[POLL ERROR] {e}", flush=True)

        time.sleep(2)

if __name__ == "__main__":
    run_messaging_worker()
