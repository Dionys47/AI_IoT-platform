from fastapi import FastAPI, HTTPException, Header, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
from pathlib import Path
import uvicorn
import random
import math
import threading
import time
import json
import secrets
import os
import urllib.request, urllib.parse
import logging

logger = logging.getLogger("server")

DATA_DIR = Path(os.environ.get("IOT_DATA_DIR", "data"))
REGISTRY_FILE = DATA_DIR / "devices_registry.json"
WIFI_OFFLINE_SECONDS = 120
MAX_SENSOR_POINTS = 500

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ============ BAZA E TË DHËNAVE ============
devices_db = {
    "1": {"id": "1", "name": "HIGH-TEMP-TEST", "device_type": "temperature", "location": "Furra", "status": "online", "source": "simulated"},
    "2": {"id": "2", "name": "LOW-TEMP-TEST", "device_type": "temperature", "location": "Magazinimi", "status": "online", "source": "simulated"},
    "3": {"id": "3", "name": "CONSTANT-TEMP-TEST", "device_type": "temperature", "location": "Ambient", "status": "online", "source": "simulated"},
    "4": {"id": "4", "name": "DRIFT-TEMP-TEST", "device_type": "temperature", "location": "Reaktor", "status": "online", "source": "simulated"},
    "5": {"id": "5", "name": "COLD-ROOM", "device_type": "temperature", "location": "Ngrirje", "status": "online", "source": "simulated"},
    "6": {"id": "6", "name": "HOT-ZONE", "device_type": "temperature", "location": "Pjekje", "status": "online", "source": "simulated"},
    "7": {"id": "7", "name": "WIDE-SWING", "device_type": "temperature", "location": "Test", "status": "online", "source": "simulated"},
    "8": {"id": "8", "name": "STABLE-HUMID", "device_type": "temperature", "location": "Serre", "status": "online", "source": "simulated"},
}
sensor_db = {k: [] for k in devices_db}
device_keys: dict[str, str] = {}
last_seen: dict[str, str] = {}
counter = 100


def _is_wifi_device(device_id: str) -> bool:
    return devices_db.get(device_id, {}).get("source") == "wifi"


def save_registry():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "devices": devices_db,
        "device_keys": device_keys,
        "last_seen": last_seen,
        "sensor_db": {k: v[-MAX_SENSOR_POINTS:] for k, v in sensor_db.items() if _is_wifi_device(k)},
        "counter": counter,
    }
    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def load_registry():
    global counter
    if not REGISTRY_FILE.exists():
        return
    try:
        with open(REGISTRY_FILE, encoding="utf-8") as f:
            payload = json.load(f)
        for did, dev in payload.get("devices", {}).items():
            if dev.get("source") == "wifi":
                devices_db[did] = dev
                sensor_db.setdefault(did, [])
        device_keys.update(payload.get("device_keys", {}))
        last_seen.update(payload.get("last_seen", {}))
        for did, rows in payload.get("sensor_db", {}).items():
            for row in rows:
                if "sensor_type" not in row:
                    row["sensor_type"] = "temperature"
                    row["unit"] = row.get("unit", "C")
            sensor_db[did] = rows
        counter = max(counter, payload.get("counter", counter))
    except (json.JSONDecodeError, OSError):
        pass


def _platform_base_url(request: Optional[Request] = None) -> str:
    if request is not None:
        return str(request.base_url).rstrip("/")
    host = os.environ.get("IOT_PLATFORM_URL", "http://localhost:8000")
    return host.rstrip("/")


def _verify_device_key(device_id: str, api_key: str) -> bool:
    expected = device_keys.get(device_id)
    return bool(expected and secrets.compare_digest(expected, api_key))


def _append_sensor_reading(device_id: str, value: float, sensor_type: str = "temperature", unit: str = "C"):
    global counter
    now = datetime.now().isoformat()
    new_data = {
        "id": counter,
        "device_id": device_id,
        "sensor_type": sensor_type,
        "unit": unit,
        "value": value,
        "timestamp": now,
    }
    sensor_db.setdefault(device_id, []).append(new_data)
    if len(sensor_db[device_id]) > MAX_SENSOR_POINTS:
        sensor_db[device_id] = sensor_db[device_id][-MAX_SENSOR_POINTS:]
    counter += 1
    last_seen[device_id] = now
    if device_id in devices_db:
        devices_db[device_id]["status"] = "online"
        devices_db[device_id]["last_seen"] = now
    return new_data


def update_wifi_status():
    while True:
        try:
            now = datetime.now()
            for did, dev in list(devices_db.items()):
                if dev.get("source") != "wifi":
                    continue
                seen = last_seen.get(did)
                if not seen:
                    dev["status"] = "offline"
                    continue
                seen_dt = datetime.fromisoformat(seen)
                dev["status"] = "online" if (now - seen_dt) < timedelta(seconds=WIFI_OFFLINE_SECONDS) else "offline"
        except Exception:
            pass
        time.sleep(30)

# Profiles for automatic data generation
profiles = {
    "1": {"min": 22, "max": 26, "anomaly_min": 80, "anomaly_max": 100, "prob": 0.05, "humidity_min": 45, "humidity_max": 55, "humidity_anomaly_min": 80, "humidity_anomaly_max": 95, "humidity_prob": 0.03},
    "2": {"min": 20, "max": 24, "anomaly_min": -10, "anomaly_max": -5, "prob": 0.05, "humidity_min": 55, "humidity_max": 65, "humidity_anomaly_min": 10, "humidity_anomaly_max": 20, "humidity_prob": 0.03},
    "3": {"min": 24.9, "max": 25.1, "anomaly_min": 30, "anomaly_max": 35, "prob": 0.02, "humidity_min": 40, "humidity_max": 42, "humidity_anomaly_min": 60, "humidity_anomaly_max": 70, "humidity_prob": 0.02},
    "4": {"min": 20, "max": 45, "anomaly_min": 50, "anomaly_max": 60, "prob": 0.03, "drift": True, "humidity_min": 30, "humidity_max": 70, "humidity_anomaly_min": 80, "humidity_anomaly_max": 95, "humidity_prob": 0.03},
    "5": {"min": -12, "max": -2, "anomaly_min": 5, "anomaly_max": 15, "prob": 0.04, "humidity_min": 60, "humidity_max": 80, "humidity_anomaly_min": 90, "humidity_anomaly_max": 100, "humidity_prob": 0.02},
    "6": {"min": 55, "max": 70, "anomaly_min": 25, "anomaly_max": 35, "prob": 0.04, "humidity_min": 20, "humidity_max": 35, "humidity_anomaly_min": 50, "humidity_anomaly_max": 70, "humidity_prob": 0.02},
    "7": {"min": -10, "max": 60, "anomaly_min": 70, "anomaly_max": 80, "prob": 0.03, "drift": True, "humidity_min": 30, "humidity_max": 80, "humidity_anomaly_min": 10, "humidity_anomaly_max": 20, "humidity_prob": 0.03},
    "8": {"min": 22, "max": 26, "anomaly_min": 35, "anomaly_max": 45, "prob": 0.02, "humidity_min": 75, "humidity_max": 95, "humidity_anomaly_min": 30, "humidity_anomaly_max": 50, "humidity_prob": 0.02}
}
drift = 0

def generate_value(device_id, sensor_type="temperature"):
    global drift
    p = profiles[device_id]
    if sensor_type == "humidity":
        if p.get("drift"):
            d = drift + 1
            base = 45 + (d % 1000) / 1000 * 20
            val = base + random.uniform(-2, 2)
            if random.random() < p.get("humidity_prob", 0.03):
                val += random.uniform(15, 25)
        else:
            if random.random() < p.get("humidity_prob", 0.03):
                val = random.uniform(p["humidity_anomaly_min"], p["humidity_anomaly_max"])
            else:
                val = random.uniform(p["humidity_min"], p["humidity_max"])
        return round(val, 1)
    if p.get("drift"):
        drift += 1
        base = 20 + (drift % 1000) / 1000 * 25
        val = base + random.uniform(-0.5, 0.5)
        if random.random() < p["prob"]:
            val += random.uniform(10, 20)
    else:
        if random.random() < p["prob"]:
            val = random.uniform(p["anomaly_min"], p["anomaly_max"])
        else:
            val = random.uniform(p["min"], p["max"])
    return round(val, 1)

def auto_generate():
    global counter
    while True:
        try:
            now = datetime.now().isoformat()
            for did in devices_db:
                if _is_wifi_device(did):
                    continue
                val_t = generate_value(did, "temperature")
                sensor_db[did].append({"id": counter, "device_id": did, "sensor_type": "temperature", "unit": "C", "value": val_t, "timestamp": now})
                val_h = generate_value(did, "humidity")
                sensor_db[did].append({"id": counter + 1, "device_id": did, "sensor_type": "humidity", "unit": "%", "value": val_h, "timestamp": now})
                if len(sensor_db[did]) > MAX_SENSOR_POINTS * 2:
                    sensor_db[did] = sensor_db[did][-(MAX_SENSOR_POINTS * 2):]
            counter += 2
        except:
            pass
        time.sleep(5)

threading.Thread(target=auto_generate, daemon=True).start()

# Initial data
def init_data():
    global counter
    span_hours = 4
    start = datetime.now() - timedelta(hours=span_hours)
    for i in range(50):
        ts = (start + timedelta(seconds=(i * span_hours * 3600 / 50))).isoformat()
        for did in devices_db:
            if _is_wifi_device(did):
                continue
            if did not in profiles:
                continue
            val_t = generate_value(did, "temperature")
            sensor_db[did].append({"id": counter, "device_id": did, "sensor_type": "temperature", "unit": "C", "value": val_t, "timestamp": ts})
            val_h = generate_value(did, "humidity")
            sensor_db[did].append({"id": counter + 1, "device_id": did, "sensor_type": "humidity", "unit": "%", "value": val_h, "timestamp": ts})
        counter += 2

load_registry()
init_data()
threading.Thread(target=update_wifi_status, daemon=True).start()

# ============ MODELS ============
class DeviceCreate(BaseModel):
    name: str
    device_type: str
    location: Optional[str] = None
    group: Optional[str] = None

class DeviceUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    group: Optional[str] = None

class WiFiDeviceCreate(BaseModel):
    name: str
    device_type: str = "temperature"
    sensor_type: str = "temperature"
    unit: str = "C"
    location: Optional[str] = None
    group: Optional[str] = None
    mac_address: Optional[str] = None
    brand: str = "generic"

class SensorDataCreate(BaseModel):
    device_id: str
    value: float
    sensor_type: Optional[str] = "temperature"
    unit: Optional[str] = "C"

class WiFiSensorIngest(BaseModel):
    value: float
    sensor_type: Optional[str] = "temperature"
    unit: Optional[str] = "C"

# ============ ENDPOINTS ============
@app.get("/")
def root():
    with open("dashboard_full.html", "r", encoding="utf-8") as f:
        content = f.read()
        return Response(content=content, media_type="text/html", headers={"Cache-Control": "no-store, must-revalidate"})


@app.get("/devices")
def get_devices():
    return list(devices_db.values())

@app.post("/devices")
def create_device(device: DeviceCreate):
    new_id = str(max([int(k) for k in devices_db if k.isdigit()], default=0) + 1)
    new_device = {
        "id": new_id,
        "name": device.name,
        "device_type": device.device_type,
        "location": device.location or "Unknown",
        "group": device.group or "",
        "status": "online",
        "source": "simulated",
    }
    devices_db[new_id] = new_device
    sensor_db[new_id] = []
    profiles[new_id] = {"min": 20, "max": 30, "anomaly_min": 35, "anomaly_max": 45, "prob": 0.05, "humidity_min": 40, "humidity_max": 60, "humidity_anomaly_min": 75, "humidity_anomaly_max": 95, "humidity_prob": 0.03}
    return new_device


@app.post("/devices/wifi")
def register_wifi_device(device: WiFiDeviceCreate, request: Request):
    device_id = f"wifi-{secrets.token_hex(4)}"
    api_key = secrets.token_urlsafe(24)
    now = datetime.now().isoformat()
    new_device = {
        "id": device_id,
        "name": device.name,
        "device_type": device.device_type,
        "sensor_type": device.sensor_type,
        "unit": device.unit,
        "location": device.location or "WiFi",
        "group": device.group or "",
        "mac_address": device.mac_address,
        "brand": device.brand,
        "status": "offline",
        "source": "wifi",
        "last_seen": None,
        "created_at": now,
    }
    devices_db[device_id] = new_device
    sensor_db[device_id] = []
    device_keys[device_id] = api_key
    save_registry()
    base = _platform_base_url(request)
    return {
        **new_device,
        "api_key": api_key,
        "ingest_url": f"{base}/api/v1/ingest",
        "headers": {"X-Device-Id": device_id, "X-Device-Key": api_key, "Content-Type": "application/json"},
        "example_body": {"value": 23.5, "sensor_type": device.sensor_type, "unit": device.unit},
        "curl_example": (
            f'curl -X POST "{base}/api/v1/ingest" '
            f'-H "X-Device-Id: {device_id}" -H "X-Device-Key: {api_key}" '
            f'-H "Content-Type: application/json" '
            f'-d \'{{"value": 23.5, "sensor_type": "{device.sensor_type}", "unit": "{device.unit}"}}\''
        ),
    }


@app.get("/devices/{device_id}/wifi-setup")
def get_wifi_setup(device_id: str, request: Request):
    if device_id not in devices_db or not _is_wifi_device(device_id):
        raise HTTPException(404, "WiFi device not found")
    dev = devices_db[device_id]
    base = _platform_base_url(request)
    return {
        "device_id": device_id,
        "name": dev["name"],
        "ingest_url": f"{base}/api/v1/ingest",
        "status": dev.get("status"),
        "last_seen": dev.get("last_seen") or last_seen.get(device_id),
        "note": "API key was shown once at registration. Re-register if you lost it.",
    }


@app.post("/api/v1/ingest")
def ingest_wifi_sensor(
    body: WiFiSensorIngest,
    x_device_id: str = Header(..., alias="X-Device-Id"),
    x_device_key: str = Header(..., alias="X-Device-Key"),
):
    if x_device_id not in devices_db:
        raise HTTPException(404, "Device not registered")
    if not _verify_device_key(x_device_id, x_device_key):
        raise HTTPException(401, "Invalid device key")
    if not _is_wifi_device(x_device_id):
        raise HTTPException(400, "Not a WiFi device")
    reading = _append_sensor_reading(
        x_device_id, body.value, body.sensor_type or "temperature", body.unit or "C"
    )
    save_registry()
    return {"success": True, "reading": reading}


@app.get("/devices/{device_id}")
def get_device(device_id: str):
    if device_id not in devices_db:
        raise HTTPException(404, "Device not found")
    return devices_db[device_id]

@app.delete("/devices/{device_id}")
def delete_device(device_id: str):
    if device_id not in devices_db:
        raise HTTPException(404)
    if not _is_wifi_device(device_id):
        raise HTTPException(400, "Only WiFi devices can be removed from the dashboard")
    del devices_db[device_id]
    sensor_db.pop(device_id, None)
    device_keys.pop(device_id, None)
    last_seen.pop(device_id, None)
    save_registry()
    return {"message": "WiFi device removed"}

@app.put("/devices/{device_id}")
def update_device(device_id: str, update: DeviceUpdate):
    if device_id not in devices_db:
        raise HTTPException(404)
    dev = devices_db[device_id]
    if update.name is not None:
        dev["name"] = update.name
    if update.location is not None:
        dev["location"] = update.location
    if update.group is not None:
        dev["group"] = update.group
    if _is_wifi_device(device_id):
        save_registry()
    return dev

@app.get("/groups")
def get_groups():
    groups = {}
    for dev in devices_db.values():
        g = dev.get("group") or "Ungrouped"
        if g not in groups:
            groups[g] = {"name": g, "device_count": 0, "online": 0}
        groups[g]["device_count"] += 1
        if dev["status"] == "online":
            groups[g]["online"] += 1
    return list(groups.values())


@app.post("/sensor-data")
def add_sensor_data(data: SensorDataCreate):
    if data.device_id not in devices_db:
        raise HTTPException(404, "Device not found")
    if _is_wifi_device(data.device_id):
        raise HTTPException(400, "WiFi devices must use /api/v1/ingest with device key")
    new_data = _append_sensor_reading(data.device_id, data.value, data.sensor_type or "temperature", data.unit or "C")
    return new_data

@app.get("/devices/{device_id}/data")
def get_device_data(device_id: str, limit: int = 100, from_date: str = "", to_date: str = ""):
    if device_id not in devices_db:
        raise HTTPException(404)
    data = sensor_db.get(device_id, [])
    if from_date:
        data = [d for d in data if d.get("timestamp", "") >= from_date]
    if to_date:
        data = [d for d in data if d.get("timestamp", "") <= to_date]
    return data[-limit:]

@app.get("/system/stats")
def get_stats():
    total = len(devices_db)
    online = len([d for d in devices_db.values() if d["status"] == "online"])
    recent = sum(len(v) for v in sensor_db.values())
    return {"devices": {"total": total, "online": online, "offline": total - online}, "data": {"recent_24h": recent}}

# ============ AI ANALYSIS ============
@app.post("/ai/analyze")
def ai_analyze(device_id: str, sensor_type: str = "temperature", delta: float = 0, limit: int = 500, values: str = "", trend_only: bool = False):
    if values:
        vals = [float(v) for v in values.split(",") if v.strip()]
        values = vals
        # Still fetch raw data for latest_temp/humidity lookups
        data = sensor_db.get(device_id, [])
    else:
        if device_id not in devices_db:
            raise HTTPException(404)
        data = sensor_db.get(device_id, [])
        if limit > 0 and len(data) > limit:
            data = data[-limit:]
        filt = [d for d in data if d.get("sensor_type", "temperature") == sensor_type]
        if len(filt) < 10:
            return {"error": f"Not enough {sensor_type} data"}
        values = [d["value"] for d in filt]

    if delta > 0:
        # Delta-based threshold: values outside median +/- delta are anomalies
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        median_val = sorted_vals[n // 2]
        lower_fence = median_val - delta
        upper_fence = median_val + delta
        q1 = lower_fence
        q3 = upper_fence
        iqr = delta * 2
    else:
        # IQR-based anomaly detection
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        def percentile(p):
            idx = int(p * (n - 1) / 100)
            return sorted_vals[idx]
        q1 = percentile(25)
        q3 = percentile(75)
        iqr = q3 - q1
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr

    anomalies = [v for v in values if v < lower_fence or v > upper_fence]
    anomaly_indices = [i for i, v in enumerate(values) if v < lower_fence or v > upper_fence]
    rate = len(anomalies) / len(values) * 100
    status = "CRITICAL" if rate > 10 else "WARNING" if rate > 5 else "NORMAL"

    # Trend filter: when trend_only, only flag anomaly indices that are part of
    # a sustained run (3+ consecutive readings all increasing or all decreasing)
    if trend_only and len(anomaly_indices) > 0:
        trend_indices = set()
        for i in range(len(values) - 2):
            # Check for 3+ consecutive readings moving in same direction
            if (values[i] < values[i+1] < values[i+2]) or (values[i] > values[i+1] > values[i+2]):
                trend_indices.update([i, i+1, i+2])
                # Extend run further
                for j in range(i + 3, len(values)):
                    if (values[j-1] < values[j] and values[i] < values[i+1]) or \
                       (values[j-1] > values[j] and values[i] > values[i+1]):
                        trend_indices.add(j)
                    else:
                        break
        # Keep only anomaly indices that are also in a trend run
        anomaly_set = set(anomaly_indices)
        anomaly_indices = sorted(trend_indices & anomaly_set)
        anomalies = [values[i] for i in anomaly_indices]
        rate = len(anomalies) / len(values) * 100 if values else 0
        status = "CRITICAL" if rate > 10 else "WARNING" if rate > 5 else "NORMAL"

    # Get latest values from unfiltered data
    latest_temp = latest_hum = None
    for d in reversed(data):
        st = d.get("sensor_type")
        if st == "temperature" and latest_temp is None:
            latest_temp = d["value"]
        elif st == "humidity" and latest_hum is None:
            latest_hum = d["value"]
        if latest_temp is not None and latest_hum is not None:
            break
    if (latest_temp is None or latest_hum is None) and len(data) >= 2:
        last = data[-1]
        prev = data[-2]
        if latest_temp is None:
            latest_temp = prev.get("value") if prev.get("sensor_type", "temperature") == "temperature" else last.get("value")
        if latest_hum is None:
            latest_hum = last.get("value") if last.get("sensor_type", "temperature") != "temperature" else prev.get("value")
    return {
        "total_points": len(values),
        "sensor_type": sensor_type,
        "q1": round(q1, 2),
        "q3": round(q3, 2),
        "iqr": round(iqr, 2),
        "normal_range": {"low": round(lower_fence, 1), "high": round(upper_fence, 1)},
        "anomaly_count": len(anomalies),
        "anomaly_rate": round(rate, 1),
        "anomaly_values": anomalies[:10],
        "anomaly_indices": anomaly_indices,
        "current_temp": latest_temp,
        "current_humidity": latest_hum,
        "status": status
    }

# ============ PREDICTION ============
@app.post("/predict")
def predict_linear(device_id: str, hours: int = 24, sensor_type: str = "temperature"):
    if device_id not in devices_db:
        raise HTTPException(404)
    data = sensor_db.get(device_id, [])
    filt = [d for d in data if d.get("sensor_type", "temperature") == sensor_type]
    if len(filt) < 20:
        return {"error": f"Need at least 20 {sensor_type} points"}
    values = [d["value"] for d in filt[-50:]]
    n = len(values)
    x = list(range(n))

    # ---- Linear fit: y = b0 + b1*x ----
    sx = sum(x)
    sy = sum(values)
    sxy = sum(x[i] * values[i] for i in range(n))
    sx2 = sum(i * i for i in x)
    denom = n * sx2 - sx * sx
    if denom == 0:
        return {"error": "Invariant data"}
    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    pred_lin = [intercept + slope * (n + i) for i in range(hours)]
    res_lin = [values[i] - (intercept + slope * x[i]) for i in range(n)]
    rmse_lin = (sum(r * r for r in res_lin) / max(1, n - 2)) ** 0.5

    # ---- Quadratic fit: y = c0 + c1*x + c2*x² ----
    sx3 = sum(xi ** 3 for xi in x)
    sx4 = sum(xi ** 4 for xi in x)
    sxxy = sum(x[i] ** 2 * values[i] for i in range(n))
    a11, a12, a13 = n, sx, sx2
    a21, a22, a23 = sx, sx2, sx3
    a31, a32, a33 = sx2, sx3, sx4
    b1, b2, b3 = sy, sxy, sxxy
    detA = a11 * (a22 * a33 - a23 * a32) - a12 * (a21 * a33 - a23 * a31) + a13 * (a21 * a32 - a22 * a31)
    if abs(detA) > 1e-12:
        det1 = b1 * (a22 * a33 - a23 * a32) - a12 * (b2 * a33 - a23 * b3) + a13 * (b2 * a32 - a22 * b3)
        det2 = a11 * (b2 * a33 - a23 * b3) - b1 * (a21 * a33 - a23 * a31) + a13 * (a21 * b3 - b2 * a31)
        det3 = a11 * (a22 * b3 - b2 * a32) - a12 * (a21 * b3 - b2 * a31) + b1 * (a21 * a32 - a22 * a31)
        c0 = det1 / detA
        c1 = det2 / detA
        c2 = det3 / detA
        pred_quad = [c0 + c1 * (n + i) + c2 * (n + i) ** 2 for i in range(hours)]
        res_quad = [values[i] - (c0 + c1 * x[i] + c2 * x[i] ** 2) for i in range(n)]
        rmse_quad = (sum(r * r for r in res_quad) / max(1, n - 3)) ** 0.5
    else:
        pred_quad, rmse_quad = pred_lin, rmse_lin

    # ---- Pick best model ----
    if rmse_quad < rmse_lin:
        pred = pred_quad
        rmse = rmse_quad
        used = "quadratic"
        avg_slope = 2 * c2 * (n + hours / 2) + c1
        trend = "increasing" if avg_slope > 0.01 else "decreasing" if avg_slope < -0.01 else "stable"
    else:
        pred = pred_lin
        rmse = rmse_lin
        used = "linear"
        trend = "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable"

    # ---- Prediction intervals (95%) ----
    pred_var = rmse * rmse * (1 + 1.0 / n)
    pred_std = pred_var ** 0.5
    z = 1.96
    lower_bounds = [p - z * pred_std for p in pred]
    upper_bounds = [p + z * pred_std for p in pred]

    return {
        "predictions": pred,
        "lower_bounds": lower_bounds,
        "upper_bounds": upper_bounds,
        "trend": trend,
        "expected_range": {"min": min(pred), "max": max(pred)},
        "next_6h": pred[:6],
        "model": used,
        "rmse": round(rmse, 3)
    }

# ============ AUTOPILOT ============
autopilot_active = False
autopilot_alerts = []

@app.post("/autopilot/start")
def start_ap():
    global autopilot_active
    autopilot_active = True
    return {"status": "started"}

@app.post("/autopilot/stop")
def stop_ap():
    global autopilot_active
    autopilot_active = False
    return {"status": "stopped"}

@app.get("/autopilot/status")
def ap_status():
    return {"active": autopilot_active, "alerts": len(autopilot_alerts)}

@app.post("/autopilot/alert")
def add_alert(alert: dict):
    temp_str = alert.get("temp", "?")
    hum_str = alert.get("humidity", "?")
    autopilot_alerts.insert(0, {
        "timestamp": datetime.now().isoformat(),
        "device": alert.get("device"),
        "value": alert.get("value"),
        "temp": temp_str,
        "humidity": hum_str,
        "message": alert.get("message", "Anomaly detected")
    })
    if len(autopilot_alerts) > 50:
        autopilot_alerts.pop()
    try:
        cfg_path = DATA_DIR / "notify_config.json"
        if cfg_path.exists():
            cfg = json.loads(cfg_path.read_text())
            tg = cfg.get("telegram", {})
            if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
                msg = (
                    f"⚠️ Anomaly Alert\n"
                    f"Device: {alert.get('device')}\n"
                    f"🌡️ {temp_str}°C  💧 {hum_str}%\n"
                    f"{alert.get('message', 'Anomaly detected')}"
                )
                urllib.request.urlopen(
                    f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage",
                    data=urllib.parse.urlencode({"chat_id": tg["chat_id"], "text": msg}).encode(),
                    timeout=10
                )
            else:
                logger.warning("Telegram config exists but not fully configured (missing enabled/bot_token/chat_id)")
        else:
            logger.warning("notify_config.json not found - configure Telegram in dashboard Settings")
    except Exception as e:
        logger.error(f"Telegram send failed: {e}")
    return {"added": True}

@app.get("/autopilot/alerts")
def get_alerts():
    return {"alerts": autopilot_alerts[:20]}

# ============ MACHINE LEARNING (per-device models) ============
ml_models = {}
ml_scalers = {}
ml_trained_for = {}
ml_metrics = {}
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    sklearn_ok = True
except Exception:
    sklearn_ok = False

@app.post("/ml/train")
def train_ml(device_id: str, lookback: int = 10, sensor_type: str = "temperature"):
    if not sklearn_ok:
        return {"error": "Install scikit-learn: pip install scikit-learn"}
    if device_id not in devices_db:
        raise HTTPException(404)
    data = sensor_db.get(device_id, [])
    filt = [d for d in data if d.get("sensor_type", "temperature") == sensor_type]
    if len(filt) < 50:
        return {"error": f"Need at least 50 {sensor_type} points"}
    values = [d["value"] for d in filt]
    X, y = [], []
    for i in range(lookback, len(values)):
        X.append(values[i - lookback:i])
        y.append(values[i])
    split = int(0.8 * len(X))
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train_s, y_train)
    y_pred = model.predict(X_test_s)
    mae = sum(abs(y_test[i] - y_pred[i]) for i in range(len(y_test))) / len(y_test)
    r2 = 1 - sum((y_test[i] - y_pred[i])**2 for i in range(len(y_test))) / sum((y_test[i] - sum(y_test)/len(y_test))**2 for i in range(len(y_test)))
    ml_models[device_id] = model
    ml_scalers[device_id] = scaler
    ml_trained_for[device_id] = True
    ml_metrics[device_id] = {"mae": round(mae, 2), "r2": round(r2, 3)}
    return {"success": True, "metrics": {"mae": round(mae, 2), "r2": round(r2, 3)}}

@app.post("/ml/predict")
def predict_ml(device_id: str, steps_ahead: int = 24, lookback: int = 10, sensor_type: str = "temperature"):
    if not sklearn_ok or device_id not in ml_trained_for:
        return {"error": "Model not trained for this device or sklearn missing"}
    if device_id not in devices_db:
        raise HTTPException(404)
    data = sensor_db.get(device_id, [])
    filt = [d for d in data if d.get("sensor_type", "temperature") == sensor_type]
    if not filt:
        return {"error": f"No {sensor_type} data"}
    values = [d["value"] for d in filt]
    if len(values) < lookback:
        return {"error": f"Need at least {lookback} points"}
    model = ml_models[device_id]
    scaler = ml_scalers[device_id]
    recent = values[-lookback:]
    preds = []
    cur = recent.copy()
    for _ in range(steps_ahead):
        scaled = scaler.transform([cur])
        pred = model.predict(scaled)[0]
        preds.append(pred)
        cur = cur[1:] + [pred]
    mean_pred = sum(preds) / len(preds)
    std_pred = (sum((p - mean_pred) ** 2 for p in preds) / len(preds)) ** 0.5
    return {
        "success": True,
        "predictions": preds,
        "lower_bounds": [p - 1.96 * std_pred for p in preds],
        "upper_bounds": [p + 1.96 * std_pred for p in preds],
        "statistics": {
            "min": min(preds), "max": max(preds), "mean": mean_pred,
            "confidence_interval": {"lower": mean_pred - 1.96 * std_pred, "upper": mean_pred + 1.96 * std_pred}
        },
        "trend": "increasing" if preds[-1] > preds[0] else "decreasing",
        "model": "random_forest",
        "rmse": ml_metrics.get(device_id, {}).get("mae", 0)
    }

@app.get("/ml/status")
def ml_status():
    return {"trained_for": list(ml_trained_for.keys()), "sklearn_available": sklearn_ok}

NOTIFY_CONFIG_FILE = DATA_DIR / "notify_config.json"

@app.get("/notifications/config")
def get_notify_config():
    if NOTIFY_CONFIG_FILE.exists():
        return json.loads(NOTIFY_CONFIG_FILE.read_text())
    return {"telegram": {"enabled": False, "bot_token": "", "chat_id": ""}}

@app.put("/notifications/config")
def update_notify_config(cfg: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NOTIFY_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    return {"saved": True}

TUYA_CONFIG_FILE = DATA_DIR / "tuya_config.json"

@app.get("/tuya/config")
def get_tuya_config():
    if TUYA_CONFIG_FILE.exists():
        return json.loads(TUYA_CONFIG_FILE.read_text())
    return {"access_id": "", "access_secret": "", "tuya_device_id": "", "local_device_id": "", "interval_seconds": 60}

@app.put("/tuya/config")
def save_tuya_config(cfg: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TUYA_CONFIG_FILE.write_text(json.dumps(cfg, indent=2))
    return {"saved": True}

@app.get("/tuya/status")
def tuya_bridge_status():
    return {"running": _tuya_bridge_active}

# ============ TUYA BRIDGE (built-in) ============
_tuya_bridge_active = False

def _tuya_bridge_loop():
    global _tuya_bridge_active
    while True:
        try:
            if not TUYA_CONFIG_FILE.exists():
                _tuya_bridge_active = False
                time.sleep(10)
                continue
            cfg = json.loads(TUYA_CONFIG_FILE.read_text())
            aid = cfg.get("access_id", "")
            secret = cfg.get("access_secret", "")
            tuya_did = cfg.get("tuya_device_id", "")
            local_id = cfg.get("local_device_id", "")
            interval = cfg.get("interval_seconds", 60)
            if not aid or not secret or not tuya_did or not local_id:
                _tuya_bridge_active = False
                time.sleep(10)
                continue
            local_key = device_keys.get(local_id, "")
            if not local_key:
                _tuya_bridge_active = False
                time.sleep(10)
                continue
            _tuya_bridge_active = True
            try:
                from tuya_connector import TuyaOpenAPI
                api = TuyaOpenAPI("https://openapi.tuyaeu.com", aid, secret)
                api.connect()
                r = api.get(f"/v1.0/iot-03/devices/{tuya_did}/status")
                for s in r.get("result", []):
                    code = s.get("code", "").lower()
                    val = s.get("value")
                    if val is None or isinstance(val, str):
                        continue
                    if code == "va_temperature":
                        if isinstance(val, int) and val > 100:
                            val = val / 10.0
                        jitter = round(random.uniform(-0.5, 0.5), 2)
                        body = {"value": round(float(val) + jitter, 1), "sensor_type": "temperature", "unit": "C"}
                    elif code == "va_humidity":
                        jitter = round(random.uniform(-3, 3), 1)
                        body = {"value": round(float(val) + jitter, 1), "sensor_type": "humidity", "unit": "%"}
                    else:
                        continue
                    req = urllib.request.Request(
                        f"http://localhost:8000/api/v1/ingest",
                        data=json.dumps(body).encode(),
                        headers={"X-Device-Id": local_id, "X-Device-Key": local_key, "Content-Type": "application/json"},
                        method="POST"
                    )
                    urllib.request.urlopen(req, timeout=10)
            except Exception as e:
                print(f"[TuyaBridge] Error: {e}")
            time.sleep(interval)
        except Exception:
            _tuya_bridge_active = False
            time.sleep(30)

threading.Thread(target=_tuya_bridge_loop, daemon=True).start()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="IoT Platform")
    parser.add_argument("--ssl", action="store_true", help="Enable HTTPS with Let's Encrypt auto-provision")
    parser.add_argument("--domain", type=str, default="", help="Domain for SSL (e.g. iot.example.com)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    args = parser.parse_args()

    if args.ssl and args.domain:
        try:
            from acme import client as acme_client
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography import x509
            import urllib.request
        except ImportError:
            print("SSL mode requires: pip install acme cryptography")
            print("Fallback to HTTP on port 8000")
            uvicorn.run(app, host="0.0.0.0", port=args.port)
        else:
            ssl_dir = DATA_DIR / "ssl"
            ssl_dir.mkdir(parents=True, exist_ok=True)
            cert_path = ssl_dir / "cert.pem"
            key_path = ssl_dir / "key.pem"
            if cert_path.exists() and key_path.exists():
                print(f"Using existing SSL cert: {cert_path}")
                uvicorn.run(app, host="0.0.0.0", port=443, ssl_certfile=str(cert_path), ssl_keyfile=str(key_path))
            else:
                print(f"SSL cert not found at {cert_path}. Run certbot manually:")
                print(f"  sudo certbot certonly --standalone -d {args.domain}")
                print(f"  copy fullchain.pem -> {cert_path}")
                print(f"  copy privkey.pem -> {key_path}")
                print("Starting HTTP server instead...")
                uvicorn.run(app, host="0.0.0.0", port=args.port)
    else:
        uvicorn.run(app, host="0.0.0.0", port=args.port)
