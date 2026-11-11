"""
Camera capture module for real-time video streaming.
Implements threaded OpenCV capture for low-latency frame streaming,
with automatic fallback to a dynamic simulated test pattern if no physical camera is accessible.
"""

import cv2
import time
import math
import threading
import numpy as np
from typing import Optional, Tuple, Union


class CameraStream:
    """Threaded camera stream providing low-latency frame acquisition."""

    def __init__(self, source: Union[int, str] = 0, width: int = 1280, height: int = 720):
        self.source = source
        self.width = width
        self.height = height
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.is_mock = False
        self.lock = threading.Lock()
        self.thread: Optional[threading.Thread] = None

        self.last_frame: Optional[np.ndarray] = None
        self.fps: float = 0.0
        self.frame_count: int = 0
        self.start_time: float = time.time()
        
        # Test pattern animation state
        self._sim_x = 200
        self._sim_y = 300
        self._sim_dx = 4
        self._sim_dy = 3

        self.start()

    def _open_camera(self) -> bool:
        """Attempts to open the OpenCV capture source."""
        try:
            # If source is digit string, convert to int
            src = int(self.source) if isinstance(self.source, str) and self.source.isdigit() else self.source
            
            # Use V4L2 backend on Linux if int index for best performance
            if isinstance(src, int):
                self.cap = cv2.VideoCapture(src, cv2.CAP_V4L2)
                if not self.cap.isOpened():
                    self.cap = cv2.VideoCapture(src)
            else:
                self.cap = cv2.VideoCapture(src)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                # Verify we can grab at least one frame
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    self.last_frame = frame
                    self.is_mock = False
                    print(f"[Camera] Successfully opened video source: {self.source} ({frame.shape[1]}x{frame.shape[0]})")
                    return True

            print(f"[Camera] Warning: Could not open camera source {self.source}. Falling back to simulated video feed.")
        except Exception as e:
            print(f"[Camera] Exception opening source {self.source}: {e}. Falling back to simulation.")

        self.is_mock = True
        return False

    def start(self):
        """Starts the background capture loop."""
        if self.is_running:
            return

        self._open_camera()
        self.is_running = True
        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()

    def _capture_worker(self):
        """Background thread worker to continuously poll the freshest frame."""
        fps_timer = time.time()
        frames_in_second = 0

        while self.is_running:
            if not self.is_mock and self.cap and self.cap.isOpened():
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    with self.lock:
                        self.last_frame = frame
                        self.frame_count += 1
                        frames_in_second += 1
                else:
                    # Brief sleep if frame failed, or reconnect
                    time.sleep(0.01)
            else:
                # Generate synthetic test frame at ~30 FPS
                frame = self._generate_simulated_frame()
                with self.lock:
                    self.last_frame = frame
                    self.frame_count += 1
                    frames_in_second += 1
                time.sleep(1.0 / 30.0)

            # Calculate actual FPS every second
            now = time.time()
            if now - fps_timer >= 1.0:
                self.fps = frames_in_second / (now - fps_timer)
                frames_in_second = 0
                fps_timer = now

    def _generate_simulated_frame(self) -> np.ndarray:
        """Generates a dynamic mock CCTV test pattern simulating room monitoring."""
        h, w = self.height, self.width
        # Dark room gradient background
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:, :] = (20, 24, 30)

        # Draw simulated room floor grid
        grid_color = (40, 48, 60)
        for x in range(0, w, 80):
            cv2.line(frame, (x, 0), (x, h), grid_color, 1)
        for y in range(0, h, 60):
            cv2.line(frame, (0, y), (w, y), grid_color, 1)

        # Draw room perspective guidelines (Corner of room)
        cv2.line(frame, (w // 2, 0), (w // 2, h // 2), (60, 70, 90), 2)
        cv2.line(frame, (w // 2, h // 2), (0, h), (60, 70, 90), 2)
        cv2.line(frame, (w // 2, h // 2), (w, h), (60, 70, 90), 2)

        # Draw a simulated moving silhouette / person figure
        self._sim_x += self._sim_dx
        self._sim_y += self._sim_dy
        if self._sim_x <= 150 or self._sim_x >= w - 150:
            self._sim_dx *= -1
        if self._sim_y <= 200 or self._sim_y >= h - 200:
            self._sim_dy *= -1

        sx, sy = int(self._sim_x), int(self._sim_y)
        # Head
        cv2.circle(frame, (sx, sy - 90), 25, (180, 190, 200), -1)
        # Torso
        cv2.ellipse(frame, (sx, sy - 20), (35, 55), 0, 0, 360, (140, 150, 170), -1)
        # Legs
        cv2.line(frame, (sx - 15, sy + 30), (sx - 20, sy + 100), (120, 130, 150), 12)
        cv2.line(frame, (sx + 15, sy + 30), (sx + 20, sy + 100), (120, 130, 150), 12)

        # Test pattern watermark
        cv2.putText(frame, "[TEST PATTERN - SIMULATED CAMERA FEED]", (30, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 200, 255), 2, cv2.LINE_AA)
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"REC: {timestamp_str}", (30, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 1, cv2.LINE_AA)

        return frame

    def get_frame(self) -> Optional[np.ndarray]:
        """Returns a copy of the latest available frame."""
        with self.lock:
            if self.last_frame is not None:
                return self.last_frame.copy()
            return None

    def get_frame_bytes(self, quality: int = 80) -> Optional[bytes]:
        """Returns JPEG encoded bytes of the latest frame."""
        frame = self.get_frame()
        if frame is not None:
            ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if ret:
                return buffer.tobytes()
        return None

    def change_source(self, new_source: Union[int, str]):
        """Changes the video source dynamically."""
        with self.lock:
            self.source = new_source
            if self.cap:
                self.cap.release()
            self._open_camera()

    def release(self):
        """Stops the capture thread and releases video resources."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()
            self.cap = None
        print("[Camera] Camera stream released.")
