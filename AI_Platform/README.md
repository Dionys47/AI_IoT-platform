# IoT & AI Platform

Real-time sensor data ingestion, live dashboard, ML predictions, anomaly detection, and Telegram/Pushbullet autopilot alerts — all in a single Python FastAPI server with no external database.

---

## Architecture

```
┌──────────────────────┐     ┌──────────────────────────────────────┐
│  ESP32 / Simulated   │────▶│  FastAPI Server (server_final.py)    │
│  Devices             │HTTP │  Port 8000                           │
│                      │     │                                      │
│  - DHT22 temp/hum    │     │  /api/v1/ingest  ← sensor data      │
│  - Simulated sensors │     │  /devices/*      ← CRUD + data      │
│  - Tuya smart plugs  │     │  /predict        ← linear/quadratic │
│                      │     │  /ml/*           ← Random Forest    │
│                      │     │  /autopilot/*    ← alerts           │
│                      │     │  /notifications  ← Telegram config  │
│                      │     │                                      │
│                      │     │  data/            ← JSON persistence │
│                      │     │  dashboard_full.html  ← SPA frontend│
│                      │     └──────────┬───────────────────────────┘
│                      │                │ WebSocket
│                      │                ▼
│                      │     ┌──────────────────────┐
│                      │     │  Browser Dashboard   │
│                      │     │  (Chart.js SPA)       │
│                      │     │                      │
│                      │     │  - Live temp/hum     │
│                      │     │  - Predictions overlay│
│                      │     │  - AI anomaly detect  │
│                      │     │  - Device manager     │
│                      │     │  - Resizable charts   │
│                      └─────│  - Dark mode          │
│                            └──────────────────────┘
```

**Key principles:**
- No external database — all data is in-memory with JSON file persistence (`data/`)
- Single server serves both REST API and dashboard HTML
- WebSocket pushes live data to all connected browsers
- Simulated devices generate data every 5 seconds for testing

---

## Quick start (Windows)

```powershell
cd C:\Users\USER\Documents\AI_Platform
.\start.ps1
```

Or double-click `START.bat`. If Docker Desktop is running, `start.ps1` uses Docker automatically.

| URL | What |
|-----|------|
| http://localhost:8000 | Full dashboard + API |
| http://localhost:8000/docs | OpenAPI docs (Swagger) |

### Manual start (Python only)

```powershell
pip install -r requirements.txt
python server_final.py
```

### Docker

```powershell
docker compose up -d --build
docker compose down
```

---

## Platform components in detail

### 1. Server (`server_final.py`)

A FastAPI application on port 8000 with these subsystems:

#### Data ingestion
- `POST /api/v1/ingest` — WiFi sensors POST with headers `X-Device-Id` and `X-Device-Key`. Auto-registers unknown devices. Accepts `{ "value": 23.5, "sensor_type": "temperature", "unit": "C" }`.
- `POST /sensor-data` — Simulated or manual data submission.
- Each reading stores: `id`, `device_id`, `sensor_type`, `unit`, `value`, `timestamp`.

#### Device management
- `GET /devices` — list all devices with status, location, sensor type.
- `POST /devices/register` — register a new device (returns API key).
- `DELETE /devices/{id}` — remove device and its data.
- `PUT /devices/{id}` — update device metadata (name, location, group, brand).
- `GET /devices/{id}/data?limit=N&from_date=F&to_date=T` — paginated data query.
- Devices are typed: `temperature` (temp+humidity), `contact` (door open/close), `tuya` (smart plug bridge).

#### Prediction engine
Two prediction systems, both now filter data by `sensor_type` (default: `"temperature"`):

**Linear/Quadratic (`POST /predict`):**
- Takes the last 50 readings of the requested sensor type.
- Fits both a linear model (`y = b0 + b1*x`) and a quadratic model (`y = c0 + c1*x + c2*x²`).
- Picks the model with lower RMSE.
- Returns 24 hourly predictions with 95% confidence intervals.
- Good for capturing overall trends (stable, increasing, decreasing).

**Random Forest ML (`POST /ml/train` + `POST /ml/predict`):**
- Requires scikit-learn installed (`pip install scikit-learn`).
- Training: creates sliding windows of `lookback` (default 10) past values to predict the next value. Uses an 80/20 train/test split. Trains a RandomForestRegressor with 100 estimators.
- Prediction: recursive multi-step — feeds each prediction back as input for the next step, up to `steps_ahead` (default 24).
- Returns predictions, 95% confidence bounds, and statistics.
- Note: Random Forest does not extrapolate beyond its training range — predictions may converge toward the mean if the trend extends far.

**Important:** Before the `sensor_type` fix, both predictors mixed temperature and humidity values together, producing garbage outputs. After the fix, they correctly filter to a single sensor type.

#### Anomaly detection (`POST /devices/{id}/analyze`)
- Uses the **IQR (Interquartile Range)** method.
- Calculates Q1, Q3, IQR = Q3 - Q1.
- Flags values outside `[Q1 - 1.5*IQR, Q3 + 1.5*IQR]` as anomalies.
- The threshold multiplier (default 1.5) is configurable via the sigma slider in the dashboard.
- Returns anomaly count, rate, normal range, and status messages.

#### Autopilot alerts
- `POST /autopilot/start` — starts a background loop that checks every 30 seconds for new anomalies.
- When an anomaly is detected, sends alerts via configured Telegram bot or Pushbullet.
- `POST /autopilot/stop` — stops the loop.
- `GET /autopilot/status` — returns active/inactive state.

#### WebSocket (`/ws`)
- Bidirectional real-time channel.
- When new sensor data arrives, the server broadcasts it to all connected WebSocket clients.
- The dashboard uses this to update charts live without polling.
- Message format: `{ "type": "data_update", "device_id": "...", "payload": { ... } }`

#### Telegram notifications
- `GET /notifications/config` — retrieve current Telegram/Pushbullet config.
- `POST /notifications/config` — save bot token, chat ID, enabled state.
- Alerts include device name, anomaly value, timestamp, and a link to the dashboard.

---

### 2. Dashboard (`dashboard_full.html`)

A single-page application served directly by the FastAPI server. All UI logic is in one HTML file to keep deployment simple.

#### Main UI sections

**📱 Devices tab:**
- Left sidebar shows all registered devices grouped by group name.
- Each device shows name, location, sensor type, brand, and online status.
- Click a device to select it and load its data.
- Remove button on hover to delete a device.
- "Add Real WiFi Sensor" panel to register new devices and copy credentials.

**📊 Overview tab:**
- **Stats bar**: device count, online sensors, total readings, latest values.
- **Time series charts**: two resizable Chart.js line charts side by side:
  - 🌡️ Temperature chart (purple line)
  - 💧 Humidity chart (green line)
- **Chart features:**
  - X-axis shows time labels (`HH:MM:SS`) from ISO timestamps — consistent between actual data and prediction overlays.
  - **Drag resize handle** (`⋮`) between the two charts — grab and drag left/right to adjust column widths. Hides on mobile.
  - Hover tooltip shows exact value and time.
  - Max 15 tick labels to avoid clutter.
- **Toolbar**: device selector, Force Data, AI Analysis, Predict 24h, ML Predict 24h, Clear Predictions, date range filter.
- **Analysis results**: anomaly count, rate, normal range, status, and highlighted anomalous points on the chart.
- **Prediction results**: trend icon, expected range, RMSE, next 6h summary, and a collapsible 24h table with confidence intervals.
- **Prediction overlays**: dashed orange line for linear/quadratic, dashed green line for Random Forest ML, with semi-transparent confidence bands.
- **ML section**: Train/status button and ML predict button.
- **Contact sensor panel**: replaces charts when a contact-type device is selected — shows open/closed status and event log.

#### Charts behavior
- **Data loading**: when a device is selected, `GET /devices/{id}/data?limit=200` fetches the last 200 readings. Temperature and humidity are separated by `sensor_type` filter.
- **Real-time updates**: a 3-second polling loop fetches new readings since the last known ID. New points are appended to the chart without redrawing the entire dataset.
- **Prediction overlays**: predictions are rendered as separate datasets using `padStart`/`padEnd` to align them after the actual data on the x-axis.
- **Labels**: both actual data and prediction labels use ISO timestamps, displayed as `HH:MM:SS` via a tick callback.
- **Resize**: the drag handle updates `grid-template-columns` in real time using `fr` units proportional to the cursor position (clamped between 20%–80%).

#### Key JavaScript functions

| Function | Purpose |
|----------|---------|
| `loadDeviceData()` | Fetches device readings, splits into temp/humidity arrays, renders charts. |
| `pollDeviceData()` | Incremental polling — fetches only new readings since last ID. |
| `renderChart()` | Creates or updates a Chart.js line chart with data, optional prediction extras, and proper label extension. |
| `updateChart()` | Central chart update orchestrator — builds separate `tempExtras`/`humExtras` arrays (predictions only go to temp chart) and re-renders both. |
| `addPredictionBands()` | Adds prediction values and confidence interval bands to an extras array. |
| `runAnalysis()` | Triggers IQR anomaly detection on the current device; highlights anomalies on the chart. |
| `runPrediction()` | Calls `/predict` for linear/quadratic forecast; renders prediction table and overlay. |
| `predictML()` | Calls `/ml/predict` for Random Forest forecast; renders ML prediction table and overlay. |
| `trainML()` | Calls `/ml/train` to train the Random Forest model on current device data. |
| `loadDevices()` | Fetches device list, builds group filter buttons and device list sidebar. |
| `localTimeStr(d)` | Formats a Date object as `HH:MM:SS` for prediction label extension. |
| `initResizeHandle()` | Sets up mousedown/mousemove/mouseup handlers for the chart column drag resize. |
| `startAutoRefresh()` | Starts the 3-second polling loop for live data updates. |
| `simulateData()` | Generates simulated temperature/humidity readings for the selected device. |
| `toggleTheme()` | Switches between light and dark mode (persisted in localStorage). |

---

### 3. ESP32 Firmware (`firmware/esp32_dht22_sensor/`)

C++ firmware for ESP32 with DHT22 sensor.

- Connects to WiFi (`GUXIM 2.4`).
- Reads DHT22 on GPIO 5.
- POSTs JSON to `http://192.168.0.193:8000/api/v1/ingest` every ~10 seconds.
- Includes temperature and humidity in separate readings with appropriate `sensor_type`.

---

## Data flow

```
ESP32 POST /api/v1/ingest
       │
       ▼
  Parse + validate (X-Device-Id + X-Device-Key)
       │
       ▼
  Store in sensor_db[device_id] (in-memory list)
       │
       ▼
  Append to data/readings_{device_id}.json
       │
       ▼
  Broadcast via WebSocket to all browsers
       │
       ▼
  Dashboard updates chart in real time
```

- Server auto-saves to JSON every 10 seconds (`save_data()`).
- Dashboard polls every 3 seconds for new readings (incremental by `id`).
- Prediction and analysis operate on the in-memory data for speed.

---

## Device types

| Type | sensor_type | value range | Chart display |
|------|-------------|-------------|---------------|
| Temperature sensor | `temperature` | ~15–40°C | Left chart (purple) |
| Humidity sensor | `humidity` | ~30–90% | Right chart (green) |
| Contact sensor | `contact` | 0 or 1 (open/close) | Event log panel |
| Tuya smart plug | `tuya` | Various | Via Tuya bridge |

Devices can have multiple sensor types — the ESP32 creates separate readings for temperature and humidity with the same `device_id`.

---

## API endpoints summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Serves `dashboard_full.html` |
| GET | `/devices` | List all devices |
| POST | `/devices/register` | Register new device |
| DELETE | `/devices/{id}` | Delete device |
| PUT | `/devices/{id}` | Update device metadata |
| GET | `/devices/{id}/data` | Get readings (limit, from/to) |
| POST | `/devices/{id}/analyze` | IQR anomaly detection |
| POST | `/api/v1/ingest` | WiFi sensor data ingestion |
| POST | `/sensor-data` | Manual/simulated data |
| POST | `/predict` | Linear/quadratic forecast (24h) |
| POST | `/ml/train` | Train Random Forest model |
| POST | `/ml/predict` | ML forecast (24 steps) |
| POST | `/autopilot/start` | Start anomaly alert loop |
| POST | `/autopilot/stop` | Stop alert loop |
| GET | `/autopilot/status` | Alert loop status |
| GET | `/notifications/config` | Get Telegram/Pushbullet config |
| POST | `/notifications/config` | Save notification config |
| GET | `/ml/status` | Check if models are trained |
| GET | `/stats` | Platform statistics |

---

## Configuration files

| File | Purpose |
|------|---------|
| `server_final.py` | Main server — all API logic, ML, WebSocket, persistence |
| `dashboard_full.html` | Complete SPA dashboard |
| `requirements.txt` | Python dependencies (pinned: `fastapi==0.104.1`, `starlette==0.27.0`) |
| `data/devices_registry.json` | Device registrations, API keys, metadata |
| `data/readings_*.json` | Per-device sensor readings (persistence) |
| `data/notify_config.json` | Telegram/Pushbullet configuration |
| `firmware/esp32_dht22_sensor/esp32_dht22_sensor.ino` | ESP32 firmware |

---

## Key design decisions

1. **No external database** — In-memory storage with JSON file persistence keeps deployment trivial. Suitable for <100K readings.
2. **Single HTML file** — The entire dashboard is one file for easy deployment. No build step, no bundler.
3. **Charts via Chart.js CDN** — No npm dependencies for the frontend. Loaded directly from CDN.
4. **Predictions filter by sensor_type** — Critical fix: the `/predict`, `/ml/train`, and `/ml/predict` endpoints filter data by `sensor_type` so temperature and humidity values are never mixed.
5. **Prediction overlays on temp chart only** — Linear/quadratic and ML predictions only appear on the temperature chart, not the humidity chart.
6. **Timestamp-based x-axis labels** — Both actual data and prediction overlays use ISO timestamps displayed as `HH:MM:SS` for a consistent time axis.

---

## What you can try

1. Pick a device from the dropdown and view live sensor charts.
2. Click **AI Analysis** for IQR anomaly detection.
3. Click **Predict 24h** for linear/quadratic trend forecast.
4. Click **Train ML Model** then **ML Predict 24h** for Random Forest forecast.
5. Drag the `⋮` handle between charts to resize columns.
6. Add simulated devices or register a real WiFi sensor.
7. Configure Telegram alerts via the Notifications tab.
8. Toggle dark mode with the ☀️/🌙 button.
