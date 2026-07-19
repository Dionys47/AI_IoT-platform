from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
import random

app = FastAPI(title="IoT Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class DeviceCreate(BaseModel):
    name: str
    device_type: str
    location: Optional[str] = None

class SensorDataCreate(BaseModel):
    device_id: str
    sensor_type: str
    value: float
    unit: str

# Database
devices_db = {}
sensor_db = {}
device_counter = 1
data_counter = 1

# Default devices
default_devices = [
    {"id": "1", "name": "HIGH-TEMP-TEST", "device_type": "temperature", "location": "Furra", "status": "online"},
    {"id": "2", "name": "LOW-TEMP-TEST", "device_type": "temperature", "location": "Magazinimi", "status": "online"},
    {"id": "3", "name": "CONSTANT-TEMP-TEST", "device_type": "temperature", "location": "Ambient", "status": "online"},
    {"id": "4", "name": "DRIFT-TEMP-TEST", "device_type": "temperature", "location": "Reaktor", "status": "online"}
]

for d in default_devices:
    devices_db[d["id"]] = d

# Create default data
def create_default_data():
    global data_counter
    now = datetime.now()
    
    # HIGH-TEMP-TEST
    high_data = []
    for i in range(30):
        high_data.append({"id": data_counter, "device_id": "1", "sensor_type": "temperature", "value": round(24 + random.uniform(-2, 2), 1), "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    for v in [82, 88, 95, 99, 85]:
        high_data.append({"id": data_counter, "device_id": "1", "sensor_type": "temperature", "value": v, "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    sensor_db["1"] = high_data
    
    # LOW-TEMP-TEST
    low_data = []
    for i in range(30):
        low_data.append({"id": data_counter, "device_id": "2", "sensor_type": "temperature", "value": round(22 + random.uniform(-2, 2), 1), "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    for v in [-8, -6, -10, -5, -7]:
        low_data.append({"id": data_counter, "device_id": "2", "sensor_type": "temperature", "value": v, "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    sensor_db["2"] = low_data
    
    # CONSTANT-TEMP-TEST
    const_data = []
    for i in range(40):
        const_data.append({"id": data_counter, "device_id": "3", "sensor_type": "temperature", "value": 25.0, "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    sensor_db["3"] = const_data
    
    # DRIFT-TEMP-TEST
    drift_data = []
    for i in range(50):
        value = 20 + (i / 50) * 25
        drift_data.append({"id": data_counter, "device_id": "4", "sensor_type": "temperature", "value": round(value, 1), "unit": "C", "timestamp": now.isoformat()})
        data_counter += 1
    sensor_db["4"] = drift_data

create_default_data()

# Endpoints
@app.get("/")
def root():
    return {"message": "IoT Platform", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/devices")
def get_devices():
    return list(devices_db.values())

@app.post("/devices")
def create_device(device: DeviceCreate):
    global device_counter
    device_id = str(device_counter + 4)
    device_counter += 1
    new_device = {
        "id": device_id,
        "name": device.name,
        "device_type": device.device_type,
        "location": device.location,
        "status": "online"
    }
    devices_db[device_id] = new_device
    if device_id not in sensor_db:
        sensor_db[device_id] = []
    return new_device

@app.delete("/devices/{device_id}")
def delete_device(device_id: str):
    if device_id not in devices_db:
        raise HTTPException(404, "Not found")
    del devices_db[device_id]
    if device_id in sensor_db:
        del sensor_db[device_id]
    return {"message": "Deleted"}

@app.post("/sensor-data")
def add_sensor_data(data: SensorDataCreate):
    global data_counter
    if data.device_id not in devices_db:
        raise HTTPException(404, "Device not found")
    new_data = {
        "id": data_counter,
        "device_id": data.device_id,
        "sensor_type": data.sensor_type,
        "value": data.value,
        "unit": data.unit,
        "timestamp": datetime.now().isoformat()
    }
    if data.device_id not in sensor_db:
        sensor_db[data.device_id] = []
    sensor_db[data.device_id].append(new_data)
    data_counter += 1
    return new_data

@app.get("/devices/{device_id}/data")
def get_device_data(device_id: str, limit: int = 100):
    if device_id not in devices_db:
        raise HTTPException(404, "Not found")
    data = sensor_db.get(device_id, [])
    return data[-limit:]

@app.get("/system/stats")
def get_stats():
    total = len(devices_db)
    online = len([d for d in devices_db.values() if d["status"] == "online"])
    recent = 0
    for d in sensor_db.values():
        recent += len(d)
    return {
        "devices": {"total": total, "online": online, "offline": total - online},
        "data": {"recent_24h": recent}
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)