from tuya_connector import TuyaOpenAPI
import requests, time, random, json
from pathlib import Path

CONFIG_FILE = Path("data/tuya_config.json")

cfg = {}
if CONFIG_FILE.exists():
    cfg = json.loads(CONFIG_FILE.read_text())

ACCESS_ID = cfg.get("access_id", "")
ACCESS_SECRET = cfg.get("access_secret", "")
TUYA_DEVICE_ID = cfg.get("tuya_device_id", "")
LOCAL_ID = cfg.get("local_device_id", "")
INTERVAL = cfg.get("interval_seconds", 60)
BASE = "https://openapi.tuyaeu.com"

if not ACCESS_ID or not ACCESS_SECRET or not TUYA_DEVICE_ID or not LOCAL_ID:
    print("ERROR: Tuya bridge not configured. Use the web GUI to configure.")
    exit(1)

# Load the device key from the server's registry
REGISTRY_FILE = Path("data/devices_registry.json")
if REGISTRY_FILE.exists():
    reg = json.loads(REGISTRY_FILE.read_text())
    LOCAL_KEY = reg.get("device_keys", {}).get(LOCAL_ID, "")
else:
    LOCAL_KEY = ""

if not LOCAL_KEY:
    print(f"ERROR: Device {LOCAL_ID} not found in registry or has no key")
    exit(1)

LOCAL_URL = f"http://localhost:8000/api/v1/ingest"

api = TuyaOpenAPI(BASE, ACCESS_ID, ACCESS_SECRET)
api.connect()
print(f"Connected | Bridge for {LOCAL_ID} read every {INTERVAL}s")

while True:
    try:
        r = api.get(f"/v1.0/iot-03/devices/{TUYA_DEVICE_ID}/status")
        for s in r.get("result", []):
            code = s.get("code", "").lower()
            val = s.get("value")
            ts = s.get("time", "")
            if val is None or isinstance(val, str):
                continue
            if code == "va_temperature":
                if isinstance(val, int) and val > 100:
                    val = val / 10.0
                jitter = round(random.uniform(-0.15, 0.15), 2)
                resp = requests.post(LOCAL_URL, json={"value": round(float(val) + jitter, 1), "sensor_type": "temperature", "unit": "C"},
                    headers={"X-Device-Id": LOCAL_ID, "X-Device-Key": LOCAL_KEY, "Content-Type": "application/json"})
                print(f"[{time.strftime('%H:%M:%S')}] Temp: {val} (+{jitter:+.2f}) -> {resp.status_code}" + (f" (Tuya: {ts})" if ts else ""))
            elif code == "va_humidity":
                jitter = round(random.uniform(-2, 2), 1)
                resp = requests.post(LOCAL_URL, json={"value": round(float(val) + jitter, 1), "sensor_type": "humidity", "unit": "%"},
                    headers={"X-Device-Id": LOCAL_ID, "X-Device-Key": LOCAL_KEY, "Content-Type": "application/json"})
                print(f"[{time.strftime('%H:%M:%S')}] Humidity: {val} (+{jitter:+.1f}) -> {resp.status_code}" + (f" (Tuya: {ts})" if ts else ""))
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error: {e}")
    time.sleep(INTERVAL)
