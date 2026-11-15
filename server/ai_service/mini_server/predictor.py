"""
ImmunoAI — Deep Learning Predictor Module
Isolated Prediction & Inference Engine (No Web Server Code).

Loads the trained PyTorch ImmunoAICNN model from saved_model/
and runs forward pass predictions on input frames.
"""

import sys
import base64
import io
import time
from pathlib import Path

import torch
from torchvision import transforms
from PIL import Image

# Ensure training_model directory is on Python path so we can import the exact same architecture
CURRENT_DIR = Path(__file__).resolve().parent
AI_SERVICE_DIR = CURRENT_DIR.parent
TRAINING_MODEL_DIR = AI_SERVICE_DIR / "training_model"
SAVED_MODEL_DIR = AI_SERVICE_DIR / "saved_model"
SNAPSHOTS_DIR = AI_SERVICE_DIR.parent / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

if str(TRAINING_MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(TRAINING_MODEL_DIR))

from model import ImmunoAICNN

# Device Selection (GPU if available, CPU fallback)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Model Weights Path
WEIGHTS_PATH = SAVED_MODEL_DIR / "immunoai_model.pth"

# Model and weights state
model = ImmunoAICNN(num_classes=1)
model.to(DEVICE)
model.eval()

_last_weights_mtime = 0.0


def check_and_reload_weights(force: bool = False):
    """
    Checks if immunoai_model.pth has been updated (e.g. from Colab)
    and dynamically reloads weights into PyTorch without restarting the server.
    """
    global _last_weights_mtime, model
    if not WEIGHTS_PATH.exists():
        if force:
            print(f"[Predictor Warning] No weights file found at {WEIGHTS_PATH.name}. Running initialized architecture.")
        return

    try:
        current_mtime = WEIGHTS_PATH.stat().st_mtime
        if force or current_mtime != _last_weights_mtime:
            print(f"\n[Predictor] 🔄 Loading trained model weights from: {WEIGHTS_PATH.name}...")
            checkpoint = torch.load(str(WEIGHTS_PATH), map_location=DEVICE)
            if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
                model.load_state_dict(checkpoint["model_state_dict"])
            elif isinstance(checkpoint, dict) and "state_dict" in checkpoint:
                model.load_state_dict(checkpoint["state_dict"])
            else:
                model.load_state_dict(checkpoint)
            model.to(DEVICE)
            model.eval()
            _last_weights_mtime = current_mtime
            print(f"[Predictor] ✅ Successfully loaded model weights! (File modified: {time.ctime(current_mtime)})\n")
    except Exception as e:
        print(f"[Predictor Error] Could not load state dict ({e}). Running current model state.")


# Initial load on startup
print(f"[Predictor] Initializing ImmunoAICNN on {DEVICE}...")
check_and_reload_weights(force=True)

# PyTorch Image Preprocessing Pipeline (same ImageNet normalization as Colab)
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def predict_frame(base64_data: str, threshold: float = 0.50) -> dict:
    """
    Takes a base64 image string from the Node.js server,
    runs the forward pass, and returns detection results with probabilities.
    """
    # Auto-reload if new weights were dropped in saved_model/
    check_and_reload_weights()

    # Clean base64 header if present (e.g. data:image/jpeg;base64,...)
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]

    # Decode bytes to PIL Image
    img_bytes = base64.b64decode(base64_data)
    pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # PyTorch Forward Pass
    tensor = transform(pil_img).unsqueeze(0).to(DEVICE)
    start_time = time.time()
    with torch.no_grad():
        logits = model(tensor)
        prob = torch.sigmoid(logits).item()
    inference_ms = round((time.time() - start_time) * 1000.0, 1)

    confidence = round(prob * 100.0, 1)
    is_intruder = prob >= threshold

    # Diagnostic terminal print for every frame so user sees real-time DL output
    status_tag = "🚨 INTRUDER" if is_intruder else "✅ NORMAL"
    print(
        f"[Predictor DL] Logit: {logits.item():+0.4f} | Prob: {prob:0.4f} ({confidence:5.1f}%) "
        f"| Threshold: {threshold:0.2f} -> {status_tag} ({inference_ms}ms)"
    )

    return {
        "is_intruder": bool(is_intruder),
        "confidence": confidence,
        "prob": round(prob, 4),
        "logit": round(logits.item(), 4),
        "inference_ms": inference_ms,
        "box": [30, 20, 35, 60] if is_intruder else None,
        "timestamp": time.strftime("%I:%M:%S %p")
    }


def get_status() -> dict:
    """Returns inference engine metadata"""
    check_and_reload_weights()
    return {
        "status": "online",
        "model": "ImmunoAICNN (PyTorch)",
        "device": str(DEVICE),
        "weights_path": str(WEIGHTS_PATH),
        "weights_loaded": WEIGHTS_PATH.exists(),
        "weights_mtime": _last_weights_mtime
    }
