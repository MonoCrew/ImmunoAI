"""
Main FastAPI application for Intruder Detection & Smart Alert System.
Integrates threaded camera acquisition, YOLO inference, WebSocket telemetry,
and REST endpoints for system control and real-time streaming.
"""

import cv2
import time
import asyncio
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import BASE_DIR, STATIC_DIR, config_manager
from camera import CameraStream
from detector import PersonDetector
from notifier import notifier

# Initialize FastAPI app
app = FastAPI(
    title="Argus Intruder Detection System",
    description="Real-Time Computer Vision Intruder Detection with Smart Alerts",
    version="1.0.0"
)

# Static and template setup
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

dist_assets = STATIC_DIR / "dist" / "assets"
if dist_assets.exists():
    app.mount("/assets", StaticFiles(directory=str(dist_assets)), name="assets")

# Shared Vision & System State
class SystemState:
    def __init__(self):
        self.camera: Optional[CameraStream] = None
        self.detector: Optional[PersonDetector] = None
        self.is_armed: bool = config_manager.get("is_armed", False)
        
        self.latest_annotated_jpeg: Optional[bytes] = None
        self.latest_meta: Dict[str, Any] = {}
        self.jpeg_lock = threading.Lock()
        
        self.active_websockets: List[WebSocket] = []
        self.main_loop: Optional[asyncio.AbstractEventLoop] = None
        
        self.is_running: bool = False
        self.process_thread: Optional[threading.Thread] = None

system = SystemState()


# --- Pydantic Request Models ---
class ArmRequest(BaseModel):
    armed: bool

class SettingsRequest(BaseModel):
    confidence_threshold: Optional[float] = None
    debounce_frames: Optional[int] = None
    reset_frames: Optional[int] = None
    email_cooldown_seconds: Optional[int] = None
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_use_tls: Optional[bool] = None
    smtp_use_ssl: Optional[bool] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_recipient: Optional[str] = None
    roi_polygon: Optional[List[List[float]]] = None


# --- WebSocket Manager ---
async def broadcast_ws(message: Dict[str, Any]):
    """Broadcasts a JSON message to all active WebSocket clients."""
    disconnected = []
    for ws in list(system.active_websockets):
        try:
            await ws.send_json(message)
        except Exception:
            disconnected.append(ws)
    for ws in disconnected:
        if ws in system.active_websockets:
            system.active_websockets.remove(ws)


def safe_broadcast_from_thread(message: Dict[str, Any]):
    """Dispatches a message onto the main asyncio loop from a background thread."""
    if system.main_loop and system.main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_ws(message), system.main_loop)


# --- Computer Vision Background Pipeline ---
def vision_processing_pipeline():
    """
    Dedicated thread running the high-performance CV inference loop.
    Decouples YOLO inference from HTTP streaming clients to ensure maximum frame rate.
    """
    print("[Pipeline] Vision processing loop started.")
    prev_alert_state = False

    while system.is_running:
        raw_frame = system.camera.get_frame() if system.camera else None
        if raw_frame is None:
            time.sleep(0.02)
            continue

        # Run YOLO detection & debounce
        annotated_frame, meta = system.detector.process_frame(
            raw_frame,
            is_armed=system.is_armed
        )

        # Handle Intrusion Alert Edge Trigger
        if meta.get("is_new_breach", False):
            print(f"[Pipeline] 🚨 CONFIRMED BREACH! Persons in Zone: {meta['zone_person_count']}")
            event_record = notifier.dispatch_alert(annotated_frame, meta)
            
            # Thread-safe broadcast alert to UI
            safe_broadcast_from_thread({
                "type": "intrusion_alert",
                "meta": meta,
                "event": event_record
            })

        # Handle Intrusion Cleared Edge Trigger
        if prev_alert_state and not meta.get("is_intrusion_active", False):
            safe_broadcast_from_thread({
                "type": "intrusion_cleared",
                "meta": meta
            })
        prev_alert_state = meta.get("is_intrusion_active", False)

        # Encode annotated frame as JPEG for MJPEG stream
        ret, buffer = cv2.imencode('.jpg', annotated_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            with system.jpeg_lock:
                system.latest_annotated_jpeg = buffer.tobytes()
                system.latest_meta = meta

        # Sleep briefly to target ~25-30 FPS to prevent unnecessary CPU load
        time.sleep(0.025)

    print("[Pipeline] Vision processing loop terminated.")


# --- Application Lifecycle ---
@app.on_event("startup")
async def startup_event():
    """Initializes camera, detector, and background vision loop on application startup."""
    print("[Startup] Initializing Argus System components...")
    system.main_loop = asyncio.get_running_loop()
    
    cam_source = config_manager.get("camera_source", 0)
    system.camera = CameraStream(
        source=cam_source,
        width=config_manager.get("camera_width", 1280),
        height=config_manager.get("camera_height", 720)
    )

    system.detector = PersonDetector(
        model_name=config_manager.get("model_name", "yolov8n.pt"),
        confidence_threshold=config_manager.get("confidence_threshold", 0.50),
        debounce_frames=config_manager.get("debounce_frames", 4),
        reset_frames=config_manager.get("reset_frames", 3),
        roi_polygon=config_manager.get("roi_polygon", [])
    )

    system.is_armed = config_manager.get("is_armed", False)
    system.is_running = True

    system.process_thread = threading.Thread(target=vision_processing_pipeline, daemon=True)
    system.process_thread.start()
    print("[Startup] System fully initialized and ready.")


@app.on_event("shutdown")
def shutdown_event():
    """Releases camera and worker resources on shutdown."""
    print("[Shutdown] Releasing system resources...")
    system.is_running = False
    if system.camera:
        system.camera.release()
    print("[Shutdown] Completed.")


# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def get_dashboard(request: Request):
    """Renders the main security operations dashboard (React frontend)."""
    dist_index = STATIC_DIR / "dist" / "index.html"
    if dist_index.exists():
        return FileResponse(str(dist_index))
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "is_armed": system.is_armed,
            "cooldown_remaining": notifier.get_cooldown_remaining()
        }
    )


def mjpeg_frame_generator():
    """Generates MJPEG multipart stream for HTTP video player."""
    while system.is_running:
        with system.jpeg_lock:
            frame_bytes = system.latest_annotated_jpeg

        if frame_bytes is not None:
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
            )
        time.sleep(0.033)  # ~30 FPS


@app.get("/video_feed")
def video_feed():
    """MJPEG live video stream endpoint."""
    return StreamingResponse(
        mjpeg_frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.post("/api/arm")
async def toggle_arm(payload: ArmRequest):
    """Sets the Armed/Disarmed monitoring status."""
    system.is_armed = payload.armed
    config_manager.set("is_armed", payload.armed)
    
    state_str = "ARMED & PATROLLING" if system.is_armed else "DISARMED (PASSIVE)"
    print(f"[API] Monitoring state changed: {state_str}")

    # Broadcast state change to all dashboards
    await broadcast_ws({
        "type": "arm_state_changed",
        "is_armed": system.is_armed,
        "message": f"System state switched to {state_str}."
    })

    return {
        "success": True,
        "is_armed": system.is_armed,
        "status": state_str
    }


@app.get("/api/status")
def get_status():
    """Returns current runtime telemetry and system status."""
    with system.jpeg_lock:
        meta = system.latest_meta.copy()

    return {
        "is_armed": system.is_armed,
        "camera_fps": round(system.camera.fps if system.camera else 0.0, 1),
        "is_mock_camera": system.camera.is_mock if system.camera else False,
        "cooldown_remaining": notifier.get_cooldown_remaining(),
        "is_intrusion_active": meta.get("is_intrusion_active", False),
        "zone_person_count": meta.get("zone_person_count", 0),
        "consecutive_detections": meta.get("consecutive_detections", 0),
        "highest_confidence": meta.get("highest_confidence", 0.0),
        "events_count": len(notifier.event_history)
    }


@app.get("/api/events")
def get_events():
    """Returns the history of recorded intrusion events."""
    return {
        "success": True,
        "events": notifier.event_history
    }


@app.post("/api/manual-snapshot")
def manual_snapshot():
    """Takes an on-demand manual snapshot from the live camera feed."""
    frame = system.camera.get_frame() if system.camera else None
    if frame is None:
        raise HTTPException(status_code=500, detail="Camera frame unavailable")

    filepath, web_url = notifier.save_snapshot(frame, prefix="manual")
    return {
        "success": True,
        "snapshot_url": web_url,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }


@app.get("/api/settings")
def get_settings():
    """Returns application configuration with masked secrets."""
    return config_manager.to_safe_dict()


@app.post("/api/settings")
def update_settings(payload: SettingsRequest):
    """Updates runtime parameters and persists to settings.json."""
    data = payload.dict(exclude_unset=True)

    # Don't overwrite password if masked string passed back
    if data.get("smtp_password") in ["••••••••", "", None]:
        data.pop("smtp_password", None)

    config_manager.update(data)

    # Update live detector parameters
    if system.detector:
        system.detector.update_settings(
            confidence_threshold=data.get("confidence_threshold"),
            debounce_frames=data.get("debounce_frames"),
            reset_frames=data.get("reset_frames"),
            roi_polygon=data.get("roi_polygon")
        )

    return {"success": True, "message": "Settings updated successfully."}


@app.post("/api/test-email")
def test_email():
    """Triggers an immediate test email to verify SMTP configuration."""
    result = notifier.test_smtp_connection()
    return result


# --- WebSocket Endpoint ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handles real-time bi-directional telemetry and alert push notifications."""
    await websocket.accept()
    system.active_websockets.append(websocket)

    # Send initial state snapshot
    await websocket.send_json({
        "type": "initial_state",
        "is_armed": system.is_armed,
        "cooldown_remaining": notifier.get_cooldown_remaining(),
        "recent_events": notifier.event_history[:10]
    })

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "toggle_arm":
                system.is_armed = not system.is_armed
                config_manager.set("is_armed", system.is_armed)
                await broadcast_ws({
                    "type": "arm_state_changed",
                    "is_armed": system.is_armed
                })

            elif action == "ping":
                await websocket.send_json({"type": "pong", "time": time.time()})

    except WebSocketDisconnect:
        if websocket in system.active_websockets:
            system.active_websockets.remove(websocket)
    except Exception:
        if websocket in system.active_websockets:
            system.active_websockets.remove(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
