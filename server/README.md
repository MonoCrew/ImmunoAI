# ImmunoAI — Deep Learning Backend & Model Training Guide

This directory contains the complete PyTorch Deep Learning pipeline, dataset preprocessor, and FastAPI backend server for the **ImmunoAI Intruder Detection System** term project.

---

## 1. Environment & Setup (Anaconda `utility` Environment)

As requested, this project runs strictly inside your existing Anaconda **`utility`** environment to protect your Linux system Python.

To activate the environment:
```bash
conda activate utility
```

---

## 2. Dataset Setup (When Your Data is Downloaded)

When you download your Kaggle or custom dataset, place the images into the `server/data/` directory.

### Recommended Structure:
```
server/data/
├── train/
│   ├── normal/       # CCTV frames of empty rooms, background, pets
│   └── intruder/     # CCTV frames containing people / intruders
└── val/
    ├── normal/
    └── intruder/
```

> **Note**: Even if your dataset is a single folder with `normal/` and `intruder/` subfolders without `train`/`val` split, `dataset.py` automatically splits it **80% training / 20% validation** for you!

---

## 3. Training Your Model (`train.py`)

Once your dataset is placed in `server/data/`, run:

```bash
cd server
python train.py --epochs 15 --batch-size 32 --lr 0.001
```

### What happens during training:
1. **Data Augmentation**: Images are randomly flipped horizontally, rotated ($\pm 10^\circ$), and color-jittered to handle camera angles and night/day lighting variations.
2. **Loss Function**: Evaluated using **Binary Cross-Entropy with Logits (`BCEWithLogitsLoss`)**.
3. **Optimization**: Updated with **Adam Optimizer** and a learning rate scheduler (`ReduceLROnPlateau`).
4. **Best Weights**: Automatically saved to `server/weights/immunoai_model.pth`.
5. **Viva Graphs**: Exports high-resolution **`evaluation_curves.png`** (Loss & Accuracy curves) for your presentation slides!

---

## 4. Running the Backend Server (`main.py`)

To start the FastAPI live server:

```bash
cd server
python main.py
```
*(Or `uvicorn main:app --reload --port 8000`)*

- **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Live Video Stream**: [http://localhost:8000/api/stream/cam1](http://localhost:8000/api/stream/cam1)
- **WebSocket Alerts**: `ws://localhost:8000/ws/alerts`

The React frontend automatically connects to `http://localhost:8000` and displays real-time alerts whenever an intruder is detected while **Protection Mode** is ARMED.

---

## 5. Viva Defense Cheat-Sheet (For Mohsin, Anam & Maliha)

### Q1: "Describe your CNN architecture and why you designed it this way."
- **Answer**: 
  *"We designed `ImmunoAICNN`, a 4-block hierarchical Deep CNN in PyTorch:*
  - *Early blocks (Conv 1–2 with 32 and 64 filters) extract low-level edges and textures.*
  - *Deeper blocks (Conv 3–4 with 128 and 256 filters) capture high-level human contours and silhouettes.*
  - *We used Batch Normalization after every convolution to stabilize internal covariate shift and accelerate convergence.*
  - *Instead of heavy dense layers, we used **Global Adaptive Average Pooling (1x1)** followed by a regularized linear head with **Dropout (p=0.4)** to prevent overfitting, resulting in 405,409 trainable parameters that run at 30+ FPS in real time."*

### Q2: "Why Binary Cross-Entropy with Logits Loss?"
- **Answer**: 
  *"Because `BCEWithLogitsLoss` combines the Sigmoid activation and standard Cross-Entropy using the log-sum-exp trick. This provides numerical stability and prevents vanishing or exploding gradients when probabilities approach 0 or 1."*

### Q3: "How does the system distinguish between normal activity and an intrusion?"
- **Answer**: 
  *"Through our **Protection Mode gating state**: when Standby, the camera runs normal surveillance preview. When ARMED, every incoming frame passes through our PyTorch inference pipeline. If probability $P(\text{Intruder}) \ge 0.70$, the backend saves a timestamped snapshot to disk, logs it into SQLite, and broadcasts a zero-latency alert over WebSockets to trigger the siren and UI notification."*
