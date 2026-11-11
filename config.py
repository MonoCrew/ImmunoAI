"""
Configuration module for Intruder Detection & Smart Alert System.
Handles runtime configuration, environment variables, and persistent settings.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
SNAPSHOTS_DIR = STATIC_DIR / "snapshots"
SETTINGS_FILE = BASE_DIR / "settings.json"

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG: Dict[str, Any] = {
    # System state
    "is_armed": False,
    
    # Camera settings
    "camera_source": 0,  # 0 for default webcam, or string path/URL
    "camera_width": 1280,
    "camera_height": 720,
    "camera_fps": 30,

    # Detection & Debounce
    "model_name": "yolov8n.pt",
    "confidence_threshold": 0.50,
    "target_classes": [0],  # 0 is 'person' in MS COCO
    "debounce_frames": 4,   # Consecutive frames with detection required to confirm intrusion
    "reset_frames": 3,      # Consecutive frames without detection before resetting breach state
    
    # Region of Interest (normalized 0.0 to 1.0 coordinates [[x, y], ...])
    # Empty list means full frame is monitored
    "roi_polygon": [],

    # Alert & Email Rate Limiting
    "email_cooldown_seconds": 45,  # Anti-spam cooldown window
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_use_tls": True,
    "smtp_use_ssl": False,
    "smtp_username": "",
    "smtp_password": "",
    "smtp_recipient": "",
    "enable_email": False,
    "email_subject": "⚠️ SECURITY ALERT: Intrusion Detected in Monitored Area"
}


class ConfigManager:
    """Manages application settings with JSON file persistence."""
    
    def __init__(self):
        self._config = DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Loads configuration from settings.json if present, otherwise uses defaults."""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                    self._config.update(stored)
            except Exception as e:
                print(f"[Config] Error loading {SETTINGS_FILE}: {e}. Using defaults.")

    def save(self):
        """Saves current configuration to settings.json."""
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4)
        except Exception as e:
            print(f"[Config] Error saving {SETTINGS_FILE}: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True):
        self._config[key] = value
        if auto_save:
            self.save()

    def update(self, new_settings: Dict[str, Any], auto_save: bool = True):
        for k, v in new_settings.items():
            if k in self._config:
                self._config[k] = v
        if auto_save:
            self.save()

    def to_safe_dict(self) -> Dict[str, Any]:
        """Returns configuration dictionary with sensitive credentials masked."""
        safe = self._config.copy()
        if safe.get("smtp_password"):
            safe["smtp_password"] = "••••••••" if safe["smtp_password"] else ""
        return safe

    @property
    def config(self) -> Dict[str, Any]:
        return self._config


config_manager = ConfigManager()
