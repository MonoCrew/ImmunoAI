"""
ImmunoAI — Real-Time Deep Learning Inference Engine
Runs the PyTorch ImmunoAICNN model on camera frames to detect intruders.
"""

import time
from pathlib import Path
import cv2
import torch
from torchvision import transforms
from PIL import Image

from model import get_model
from config import (
    MODEL_WEIGHTS_PATH,
    CONFIDENCE_THRESHOLD,
    IMAGE_SIZE,
    SNAPSHOTS_DIR
)
from database import add_incident


class IntruderDetector:
    def __init__(self, weights_path: str = None, threshold: float = CONFIDENCE_THRESHOLD):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        target_weights = weights_path or str(MODEL_WEIGHTS_PATH)

        self.model = get_model(target_weights, device=self.device)
        self.threshold = threshold
        self.last_alert_time = 0.0
        self.alert_cooldown = 4.0  # Seconds between snapshot triggers to prevent flooding

        # Standard Preprocessing Pipeline
        self.transform = transforms.Compose([
            transforms.Resize(IMAGE_SIZE),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])

    def infer_frame(self, frame_bgr):
        """
        Runs model forward pass on a single OpenCV BGR frame.
        Returns:
            is_intruder (bool)
            confidence (float 0.0 - 100.0)
            inference_ms (float)
        """
        if frame_bgr is None:
            return False, 0.0, 0.0

        # Preprocessing: BGR -> RGB -> PIL -> Tensor
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)
        tensor = self.transform(pil_img).unsqueeze(0).to(self.device)

        start_time = time.time()
        with torch.no_grad():
            logits = self.model(tensor)
            prob = torch.sigmoid(logits).item()
        inference_ms = (time.time() - start_time) * 1000.0

        confidence = round(prob * 100.0, 1)
        is_intruder = prob >= self.threshold

        return is_intruder, confidence, round(inference_ms, 1)

    def process_and_alert(self, frame_bgr, is_armed: bool):
        """
        If protection mode is ARMED and intruder is detected,
        saves a snapshot and records an incident in SQLite.
        """
        is_intruder, confidence, inference_ms = self.infer_frame(frame_bgr)

        # Only trigger alert if system is ARMED and cooldown has elapsed
        current_time = time.time()
        if is_armed and is_intruder and (current_time - self.last_alert_time >= self.alert_cooldown):
            self.last_alert_time = current_time

            # Save snapshot to disk
            snap_filename = f"snap_{int(current_time)}.jpg"
            snap_path = SNAPSHOTS_DIR / snap_filename
            cv2.imwrite(str(snap_path), frame_bgr)

            # Record incident in SQLite
            image_url = f"/snapshots/{snap_filename}"
            details = f"Intruder detected with {confidence}% confidence. Inference time: {inference_ms}ms."

            incident_data = add_incident(
                confidence=f"{confidence}%",
                threat_level="High Alert",
                image_url=image_url,
                details=details,
                box="30,20,35,60"
            )

            alert_payload = {
                "type": "INTRUDER_DETECTED",
                "cameraId": "cam1",
                "cameraName": "Attached System Camera",
                "location": "Perimeter Surveillance Feed",
                "confidence": confidence,
                "timestamp": incident_data["timestamp"],
                "box": [30, 20, 35, 60],
                "imageUrl": image_url,
                "inference_ms": inference_ms,
                "message": f"🚨 INTRUDER DETECTED ({confidence}% Confidence)!"
            }

            return alert_payload

        return None
