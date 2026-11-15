import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
SNAPSHOTS_DIR = BASE_DIR / "snapshots"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "weights"

# Ensure directories exist
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Model Settings
MODEL_WEIGHTS_PATH = MODELS_DIR / "immunoai_model.pth"
IMAGE_SIZE = (224, 224)
CONFIDENCE_THRESHOLD = 0.70  # 70% threshold for intruder alarm

# Database
DB_PATH = BASE_DIR / "immunoai.db"

# Server Settings
HOST = "0.0.0.0"
PORT = 8000
FRONTEND_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
]
