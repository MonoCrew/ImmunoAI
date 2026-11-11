# 🛡️ Argus: Real-Time Intruder Detection & Smart Alert System

An end-to-end computer vision security monitoring system built with **FastAPI**, **Ultralytics YOLO (COCO person class)**, **OpenCV**, and a **Cybersecurity Operations Dashboard**.

---

## 📌 Features

- **Passive vs. Armed Monitoring Modes**:
  - **Disarmed (Passive Mode)**: Streams real-time video feed at low latency without firing alerts or sending emails.
  - **Armed (Active Patrol Mode)**: Actively evaluates every frame for human presence, triggers immediate web dashboard alerts, sounds an emergency siren, and dispatches email notifications with attached incident snapshots.
- **Intrusion Debounce Filter (Anti-False-Positive)**: Requires person detections across consecutive frames (default: 4 frames) before confirming an intrusion, eliminating flickers caused by shadows or single-frame camera noise.
- **Rate-Limited Email Dispatcher**: Utilizes standard Python `smtplib` and `email` with a configurable anti-spam cooldown window (default: 45 seconds). Automatically falls back to local snapshot simulation if credentials are not yet configured.
- **Thread-Decoupled Vision Pipeline**: Video capture, YOLO inference, and HTTP/WebSocket streaming run on independent threads for low latency and zero buffering lag.
- **Hardware-Resilient Fallback**: Automatically falls back to an animated synthetic CCTV test pattern if no physical camera or webcam is connected.
- **Modern Security Dashboard**: Dark cyber-themed UI built with Tailwind CSS, Lucide icons, live telemetry (FPS, debounce status), Web Audio emergency siren, incident snapshot lightbox, and live audit log.

---

## 📂 Project Structure

```
├── start.sh              # 🚀 Unified Interactive CLI Launcher for Linux / macOS
├── start.bat             # 🚀 Unified Interactive CLI Launcher for Windows
├── app.py                # FastAPI server, REST routes, WebSocket broadcaster, MJPEG stream
├── camera.py             # Threaded OpenCV capture & synthetic fallback pattern generator
├── detector.py           # YOLO person detector, ROI boundary checks, consecutive debounce logic
├── notifier.py           # Rate-limited email notifier with snapshot attachments and simulation
├── config.py             # Configuration manager with settings.json persistence
├── requirements.txt      # Python dependencies
├── settings.json         # Runtime configuration (persisted)
├── yolov8n.pt            # Pre-trained YOLOv8 weights
├── static/
│   ├── dist/             # Production build of the React + Tailwind application
│   │   ├── index.html
│   │   └── assets/
│   └── snapshots/        # Local storage directory for captured breach images
└── frontend/             # React 18 + Tailwind CSS + Lucide source code (Vite)
    ├── src/
    │   ├── App.jsx       # Single-page executive UI with zero-scroll layout
    │   ├── main.jsx
    │   └── index.css     # Soft shadows, holographic gradients, frosted glass
    ├── package.json
    ├── tailwind.config.js
    └── vite.config.js
```

---

## 🚀 Unified One-File Interactive Launcher

No need to memorize terminal commands or install Conda. Users can simply run one file to open the interactive CLI dashboard:

### 🐧 For Linux / macOS Users:
```bash
./start.sh
```

### 🪟 For Windows Users:
Double-click **`start.bat`** (or type `start.bat` in Command Prompt / PowerShell).

---

### 🖥️ What the Interactive CLI Launcher Looks Like:

```text
============================================================
       ARGUS // INTRUDER DETECTION & ALERT SYSTEM           
                 Autonomous Vision Sentinel                 
============================================================
  OS: Linux (x86_64) | Env: Python 3.10 (pip)
------------------------------------------------------------
  [1] 🚀 Start Security Server (Single-Page App on :8000)
  [2] ⚡ Start React Dev Mode  (Backend :8000 + Vite :5173)
  [3] 📦 Install / Update Dependencies (Python & Node.js)
  [4] 🧪 Run Diagnostic & Hardware Check
  [5] ❌ Exit
------------------------------------------------------------
  Enter choice [1-5]: 
```

### ✨ Smart Features Built Into the Launcher:
- **Works with plain `pip` or Conda**: You don't need Conda installed. It automatically detects whether you have Conda, an active Virtualenv, or standard Python with `pip`.
- **System Protection**: Automatically creates and activates an isolated `.venv` to prevent polluting global system packages.
- **Auto-Dependency Prompt**: If a user selects `[1]` to start the server before installing packages, it catches the error and asks:
  ```text
  ❌ Server start failed: Required dependencies are missing!
  Would you like to install them now? [Y/n]: 
  ```
  Pressing `Y` automatically installs everything and starts the server.
- **Node.js is Optional**: The production-ready React Single-Page App is pre-compiled in `static/dist/`. If a teammate doesn't have Node.js, the server runs the sleek React UI seamlessly out of the box! Node.js is only required if they want to edit the React frontend with Vite HMR (`Option [2]`).
- **Hardware Diagnostic Scan (`Option [4]`)**: Verifies Python, webcam devices (`/dev/video*`), YOLO weights, and OpenCV without starting the web server.

---

### 3. Step-by-Step Verification

#### Step 1: Verify Passive Video Feed
1. Open `http://localhost:8000`.
2. Notice the top status pill: **DISARMED (PASSIVE)** with an emerald green glow.
3. Walk in front of the camera or test in front of the lens:
   - Green bounding boxes appear tracking people in passive mode.
   - **No alerts or emails are triggered.**

#### Step 2: Arm the Monitoring System
1. Click the **Master Arm Guard** switch on the dashboard.
2. The UI switches to **ARMED & ACTIVE** with a pulsing red aura.
3. The video banner indicates `[ARMED & ACTIVE] MONITORING ROOM`.

#### Step 3: Test Intruder Detection & Debounce
1. Step into the camera's field of view.
2. Watch the **DEBOUNCE** counter at the bottom right corner of the video player:
   - Frame 1/4 ➔ 2/4 ➔ 3/4 ➔ **4/4 (CONFIRMED BREACH)**.
3. Upon reaching the debounce threshold:
   - The video monitor displays a flashing red alert border.
   - The top banner drops down: **🚨 INTRUSION DETECTED IN MONITORED SPACE!**
   - The browser emits a 2-tone emergency siren (Web Audio API).
   - An incident snapshot is saved to `static/snapshots/` and appears in the **Incident Snapshots** gallery.
   - An event record is logged in the **System Audit Log**.

#### Step 4: Configure Email Alerts (Optional)
1. Click the **Settings (gear icon)** at the top right of the dashboard.
2. In the **Email Alert Dispatcher (SMTP)** section, fill in your SMTP details:
   - **SMTP Server**: `smtp.gmail.com`
   - **SMTP Port**: `587`
   - **Sender Email**: `your_email@gmail.com`
   - **Password**: Google 16-character **App Password** (Generate at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords))
   - **Alert Recipient Email**: `recipient@example.com`
3. Click **Send Test Email** to verify SMTP connectivity.
4. Click **Save Changes**.
5. When armed and an intruder breaches the area, an HTML security email with the incident snapshot attached will be sent to the recipient, adhering to the 45-second anti-spam cooldown window.

> **Note**: If SMTP credentials are left blank, the system automatically runs in **Simulation Mode**—it saves all incident snapshots locally and updates the dashboard without errors.

---

## ⚙️ Configuration & REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Main Web Dashboard |
| `/video_feed` | `GET` | MJPEG streaming video endpoint |
| `/api/arm` | `POST` | Toggle Arm/Disarm: `{"armed": true/false}` |
| `/api/status` | `GET` | Get runtime telemetry (FPS, counts, cooldown) |
| `/api/events` | `GET` | Retrieve list of past intrusion snapshots |
| `/api/manual-snapshot` | `POST` | Capture an instant snapshot from camera |
| `/api/settings` | `GET` / `POST` | Read or update runtime configuration |
| `/api/test-email` | `POST` | Test SMTP connection and alert dispatch |
| `/ws` | `WebSocket` | Real-time bi-directional telemetry and breach push |
