"""
ImmunoAI — FastAPI Backend Server & WebSocket Alert Broadcaster
Connects OpenCV Video Ingestion, PyTorch Deep Learning Inference,
SQLite Incident Persistence, and React Frontend.

Run with:
  conda activate utility
  python server/main.py
  (or uvicorn main:app --reload --port 8000)
"""

import asyncio
import json
import time
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import HOST, PORT, SNAPSHOTS_DIR
from database import init_db, get_all_incidents
from camera import VideoCamera
from detector import IntruderDetector

# In-Memory Global State
system_state = {
    "protection_mode": False,
    "confidence_threshold": 0.70,
    "active_camera": "cam1",
    "fps": 30.0,
    "model_name": "ImmunoAICNN (PyTorch)",
}

# Initialize Camera, Detector & Database
camera = VideoCamera(camera_index=0)
detector = IntruderDetector()
init_db()


# -------------------------------------------------------------
# WEBSOCKET MANAGER (Live Zero-Latency Push to React UI)
# -------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"[WebSocket] Client connected! Active clients: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            print(f"[WebSocket] Client disconnected. Active clients: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                self.disconnect(connection)


ws_manager = ConnectionManager()


# -------------------------------------------------------------
# BACKGROUND INFERENCE WORKER
# Runs model inference on camera frames when Protection Mode is ARMED
# -------------------------------------------------------------
async def background_inference_loop():
    while True:
        try:
            raw_frame = camera.get_raw_frame()
            if raw_frame is not None:
                is_armed = system_state["protection_mode"]
                alert = detector.process_and_alert(raw_frame, is_armed=is_armed)

                if alert is not None:
                    print(f"\n[ALERT] INTRUDER BREACH DETECTED ({alert['confidence']}%)!")
                    await ws_manager.broadcast(alert)

            await asyncio.sleep(0.1)  # Run check ~10 times per second
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[Inference Error]: {e}")
            await asyncio.sleep(0.5)


# Lifespan Context Manager (replaces deprecated on_event)
@asynccontextmanager
async def lifespan(app: FastAPI):
    inference_task = asyncio.create_task(background_inference_loop())
    print("\n========================================================")
    print(" ImmunoAI FastAPI Server Online!")
    print(f" API Docs: http://localhost:{PORT}/docs")
    print(f" Video Stream: http://localhost:{PORT}/api/stream/cam1")
    print(f" WebSocket Alerts: ws://localhost:{PORT}/ws/alerts")
    print("========================================================\n")
    yield
    inference_task.cancel()
    camera.release()


# Initialize FastAPI App with Lifespan
app = FastAPI(
    title="ImmunoAI — Deep Learning Intruder Detection API",
    description="Backend API and WebSocket alert server for ImmunoAI term project.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for all origins (allows React on localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount snapshots directory for static image serving
app.mount("/snapshots", StaticFiles(directory=str(SNAPSHOTS_DIR)), name="snapshots")


# -------------------------------------------------------------
# WEBSOCKET ENDPOINT (Fixed 403 Forbidden Error)
# -------------------------------------------------------------
@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG"}))
            except Exception:
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# -------------------------------------------------------------
# REST API ENDPOINTS
# -------------------------------------------------------------
class ProtectionModeRequest(BaseModel):
    enabled: bool


@app.get("/api/health")
def get_health():
    return {
        "status": "healthy",
        "model_loaded": True,
        "model_name": system_state["model_name"],
        "device": str(detector.device),
        "fps": system_state["fps"]
    }


@app.get("/api/status")
def get_status():
    return {
        "protection_mode": system_state["protection_mode"],
        "active_camera": system_state["active_camera"],
        "fps": system_state["fps"],
        "model": system_state["model_name"],
        "confidence_threshold": system_state["confidence_threshold"],
    }


@app.post("/api/protection-mode")
async def set_protection_mode(payload: ProtectionModeRequest):
    system_state["protection_mode"] = payload.enabled
    status_text = "ARMED" if payload.enabled else "STANDBY"
    print(f"[System] Protection Mode toggled: {status_text}")

    # Broadcast mode change to connected clients
    await ws_manager.broadcast({
        "type": "PROTECTION_MODE_CHANGED",
        "enabled": payload.enabled,
        "status": status_text,
        "timestamp": time.strftime("%I:%M:%S %p")
    })

    return {
        "success": True,
        "protection_mode": system_state["protection_mode"],
        "message": f"Security System is now {status_text}"
    }


@app.get("/api/intruders/snapshots")
def get_snapshots():
    incidents = get_all_incidents()
    return incidents


@app.get("/api/stream/{camera_id}")
def video_feed(camera_id: str):
    def frame_generator():
        while True:
            frame_bytes = camera.get_jpeg_bytes()
            if frame_bytes:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            time.sleep(0.033)  # ~30 FPS

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
