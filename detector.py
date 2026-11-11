"""
Object detection and intrusion evaluation module using Ultralytics YOLO.
Features person filtering (COCO class 0), Region-of-Interest (ROI) spatial verification,
consecutive-frame debounce logic, and real-time visual HUD annotation.
"""

import cv2
import time
import numpy as np
from typing import List, Tuple, Dict, Any, Optional
from ultralytics import YOLO


class PersonDetector:
    """YOLO-based person detector with debounce logic and ROI monitoring."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.50,
        debounce_frames: int = 4,
        reset_frames: int = 3,
        roi_polygon: Optional[List[List[float]]] = None
    ):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.debounce_frames = debounce_frames
        self.reset_frames = reset_frames
        self.roi_polygon = roi_polygon or []  # Normalized [[x, y], ...]

        print(f"[Detector] Initializing YOLO model: {self.model_name}...")
        self.model = YOLO(self.model_name)
        print("[Detector] YOLO model loaded successfully.")

        # Debounce state tracking
        self.consecutive_detections = 0
        self.consecutive_empty_frames = 0
        self.is_intrusion_active = False

        # Visual alert pulse counter
        self.alert_flash_counter = 0

    def update_settings(
        self,
        confidence_threshold: Optional[float] = None,
        debounce_frames: Optional[int] = None,
        reset_frames: Optional[int] = None,
        roi_polygon: Optional[List[List[float]]] = None
    ):
        """Dynamically updates detection and debounce parameters."""
        if confidence_threshold is not None:
            self.confidence_threshold = confidence_threshold
        if debounce_frames is not None:
            self.debounce_frames = debounce_frames
        if reset_frames is not None:
            self.reset_frames = reset_frames
        if roi_polygon is not None:
            self.roi_polygon = roi_polygon

    def _is_inside_roi(self, bbox: Tuple[int, int, int, int], frame_shape: Tuple[int, int]) -> bool:
        """
        Determines whether the bottom-center (footprint) or center of the detected person
        is inside the Region of Interest (ROI) polygon.
        If no ROI is defined, returns True (monitors entire frame).
        """
        if not self.roi_polygon or len(self.roi_polygon) < 3:
            return True

        h, w = frame_shape[:2]
        x1, y1, x2, y2 = bbox
        
        # Bottom-center of the person bounding box represents ground contact
        foot_x = int((x1 + x2) / 2.0)
        foot_y = int(y2)

        # Center point
        center_x = int((x1 + x2) / 2.0)
        center_y = int((y1 + y2) / 2.0)

        # Convert normalized ROI to pixel coordinates
        pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in self.roi_polygon], np.int32)
        
        foot_inside = cv2.pointPolygonTest(pts, (foot_x, foot_y), False) >= 0
        center_inside = cv2.pointPolygonTest(pts, (center_x, center_y), False) >= 0
        
        return foot_inside or center_inside

    def process_frame(
        self,
        frame: np.ndarray,
        is_armed: bool = False
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Processes a single video frame:
        - Runs YOLO person detection.
        - Checks ROI constraints.
        - Applies consecutive-frame debounce logic.
        - Overlays HUD and bounding boxes.
        
        Returns:
            annotated_frame: Frame with visual overlays.
            result_meta: Dictionary containing intrusion state, counts, and flags.
        """
        annotated_frame = frame.copy()
        h, w = frame.shape[:2]

        # In passive/disarmed mode, we can run low-cost or regular inference without alerting
        # Run YOLO with classes=[0] (person class)
        results = self.model.predict(
            source=frame,
            classes=[0],
            conf=self.confidence_threshold,
            verbose=False,
            imgsz=640
        )

        detected_persons: List[Dict[str, Any]] = []
        highest_conf = 0.0

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                if cls_id == 0 and conf >= self.confidence_threshold:
                    xyxy = box.xyxy[0].cpu().numpy().astype(int)
                    x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
                    
                    in_roi = self._is_inside_roi((x1, y1, x2, y2), (h, w))
                    
                    person_meta = {
                        "bbox": (x1, y1, x2, y2),
                        "confidence": conf,
                        "in_roi": in_roi
                    }
                    detected_persons.append(person_meta)
                    if in_roi and conf > highest_conf:
                        highest_conf = conf

        # Count persons in the monitored zone
        active_zone_persons = [p for p in detected_persons if p["in_roi"]]
        zone_person_count = len(active_zone_persons)

        # Intrusion Debounce Logic
        is_new_breach = False

        if is_armed:
            if zone_person_count > 0:
                self.consecutive_detections += 1
                self.consecutive_empty_frames = 0

                # Verify against debounce threshold
                if self.consecutive_detections >= self.debounce_frames:
                    if not self.is_intrusion_active:
                        self.is_intrusion_active = True
                        is_new_breach = True  # Edge trigger: just confirmed intrusion
            else:
                self.consecutive_empty_frames += 1
                if self.consecutive_empty_frames >= self.reset_frames:
                    self.consecutive_detections = 0
                    self.is_intrusion_active = False
        else:
            # When Disarmed, immediately reset alert state
            self.consecutive_detections = 0
            self.consecutive_empty_frames = 0
            self.is_intrusion_active = False

        # --- Draw Visual Overlays & HUD ---
        self._annotate_frame(
            annotated_frame,
            detected_persons=detected_persons,
            is_armed=is_armed,
            is_breach=self.is_intrusion_active,
            w=w,
            h=h
        )

        result_meta = {
            "is_armed": is_armed,
            "person_count": len(detected_persons),
            "zone_person_count": zone_person_count,
            "highest_confidence": round(highest_conf, 2),
            "consecutive_detections": self.consecutive_detections,
            "is_intrusion_active": self.is_intrusion_active,
            "is_new_breach": is_new_breach,
            "timestamp": time.time(),
            "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        return annotated_frame, result_meta

    def _annotate_frame(
        self,
        frame: np.ndarray,
        detected_persons: List[Dict[str, Any]],
        is_armed: bool,
        is_breach: bool,
        w: int,
        h: int
    ):
        """Renders HUD banners, ROI polygon, and detected person bounding boxes."""
        self.alert_flash_counter += 1

        # 1. Draw Region of Interest (ROI) if configured
        if self.roi_polygon and len(self.roi_polygon) >= 3:
            pts = np.array([[int(p[0] * w), int(p[1] * h)] for p in self.roi_polygon], np.int32)
            roi_color = (0, 0, 255) if is_breach else ((0, 255, 255) if is_armed else (100, 200, 100))
            cv2.polylines(frame, [pts], isClosed=True, color=roi_color, thickness=2, lineType=cv2.LINE_AA)
            cv2.putText(frame, "MONITORED ZONE", (pts[0][0], max(pts[0][1] - 8, 20)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, roi_color, 1, cv2.LINE_AA)

        # 2. Draw Detected Persons
        for p in detected_persons:
            x1, y1, x2, y2 = p["bbox"]
            conf = p["confidence"]
            in_roi = p["in_roi"]

            if is_armed and in_roi:
                # Intruder color: Bright Red
                box_color = (0, 0, 255)
                label = f"INTRUDER {int(conf * 100)}%"
            elif is_armed and not in_roi:
                # Outside ROI: Amber/Yellow warning
                box_color = (0, 200, 255)
                label = f"PERSON (OUTSIDE ROI) {int(conf * 100)}%"
            else:
                # Disarmed / Passive mode: Subtle Green
                box_color = (60, 200, 120)
                label = f"PERSON {int(conf * 100)}%"

            # Bounding rectangle with rounded aesthetics
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2, lineType=cv2.LINE_AA)
            
            # Corner accents
            corner_len = min(20, (x2 - x1) // 4, (y2 - y1) // 4)
            cv2.line(frame, (x1, y1), (x1 + corner_len, y1), box_color, 3)
            cv2.line(frame, (x1, y1), (x1, y1 + corner_len), box_color, 3)
            cv2.line(frame, (x2, y1), (x2 - corner_len, y1), box_color, 3)
            cv2.line(frame, (x2, y1), (x2, y1 + corner_len), box_color, 3)
            cv2.line(frame, (x1, y2), (x1 + corner_len, y2), box_color, 3)
            cv2.line(frame, (x1, y2), (x1, y2 - corner_len), box_color, 3)
            cv2.line(frame, (x2, y2), (x2 - corner_len, y2), box_color, 3)
            cv2.line(frame, (x2, y2), (x2, y2 - corner_len), box_color, 3)

            # Label badge
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(frame, (x1, max(0, y1 - th - 8)), (x1 + tw + 10, y1), box_color, -1)
            text_color = (255, 255, 255) if is_armed else (0, 0, 0)
            cv2.putText(frame, label, (x1 + 5, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1, cv2.LINE_AA)

        # 3. Draw Top Status Banner
        header_height = 42
        overlay = frame.copy()
        
        if is_armed:
            if is_breach:
                # Flashing Red Alert Banner
                flash = (self.alert_flash_counter // 5) % 2 == 0
                banner_color = (0, 0, 200) if flash else (0, 0, 100)
                status_text = "⚠️ [CRITICAL ALERT] INTRUSION CONFIRMED - AREA BREACHED"
                border_color = (0, 0, 255)
            else:
                banner_color = (20, 30, 40)
                deb_status = f" ({self.consecutive_detections}/{self.debounce_frames})" if self.consecutive_detections > 0 else ""
                status_text = f"🛡️ [ARMED & ACTIVE] MONITORING ROOM{deb_status}"
                border_color = (0, 140, 255)
        else:
            banner_color = (15, 25, 20)
            status_text = "🟢 [DISARMED] PASSIVE STREAMING - NO ALERTS"
            border_color = (40, 180, 80)

        cv2.rectangle(overlay, (0, 0), (w, header_height), banner_color, -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)
        cv2.line(frame, (0, header_height), (w, header_height), border_color, 2)

        cv2.putText(frame, status_text, (15, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Timestamp at top right
        now_str = time.strftime("%Y-%m-%d %H:%M:%S")
        (tw, _), _ = cv2.getTextSize(now_str, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.putText(frame, now_str, (w - tw - 15, 28),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 210, 220), 1, cv2.LINE_AA)

        # 4. Flashing screen border during active breach
        if is_armed and is_breach and ((self.alert_flash_counter // 4) % 2 == 0):
            cv2.rectangle(frame, (0, 0), (w - 1, h - 1), (0, 0, 255), 8)
