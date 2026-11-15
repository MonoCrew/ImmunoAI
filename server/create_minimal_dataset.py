"""
Generates a minimal starter dataset for ImmunoAI.
Allows testing the PyTorch training pipeline, weight generation,
and evaluation curve exports immediately before the full 2.8GB dataset is downloaded.
"""

from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TRAIN_NORMAL = DATA_DIR / "train" / "normal"
TRAIN_INTRUDER = DATA_DIR / "train" / "intruder"
VAL_NORMAL = DATA_DIR / "val" / "normal"
VAL_INTRUDER = DATA_DIR / "val" / "intruder"

for folder in [TRAIN_NORMAL, TRAIN_INTRUDER, VAL_NORMAL, VAL_INTRUDER]:
    folder.mkdir(parents=True, exist_ok=True)


def create_sample_image(is_intruder: bool, seed: int) -> Image.Image:
    np.random.seed(seed)

    # Base background (room / wall colors with lighting variation)
    base_color = (
        np.random.randint(180, 230),
        np.random.randint(180, 230),
        np.random.randint(190, 240),
    )
    img = Image.new("RGB", (224, 224), color=base_color)
    draw = ImageDraw.Draw(img)

    # Add floor / perspective lines (CCTV room perspective)
    draw.line([(0, 160), (224, 160)], fill=(120, 120, 130), width=2)
    draw.polygon([(0, 160), (224, 160), (224, 224), (0, 224)], fill=(140, 135, 130))

    if is_intruder:
        # Draw simulated human silhouette (head, torso, legs)
        x_center = np.random.randint(70, 150)
        y_top = np.random.randint(30, 60)
        clothing_color = (
            np.random.randint(20, 60),
            np.random.randint(20, 60),
            np.random.randint(20, 60),
        )

        # Head
        draw.ellipse(
            [x_center - 12, y_top, x_center + 12, y_top + 24],
            fill=(180, 140, 110),
        )
        # Torso / Jacket
        draw.rectangle(
            [x_center - 20, y_top + 24, x_center + 20, y_top + 80],
            fill=clothing_color,
        )
        # Legs / Pants
        draw.line([(x_center - 10, y_top + 80), (x_center - 12, y_top + 130)], fill=(30, 30, 40), width=8)
        draw.line([(x_center + 10, y_top + 80), (x_center + 12, y_top + 130)], fill=(30, 30, 40), width=8)

    # Add minor noise / camera grain
    return img


def generate_all():
    print("[Dataset Generator] Creating minimal starter dataset in server/data/ ...")

    # Generate Train Normal (20 images)
    for i in range(20):
        img = create_sample_image(is_intruder=False, seed=i)
        img.save(TRAIN_NORMAL / f"normal_train_{i:03d}.jpg")

    # Generate Train Intruder (20 images)
    for i in range(20):
        img = create_sample_image(is_intruder=True, seed=100 + i)
        img.save(TRAIN_INTRUDER / f"intruder_train_{i:03d}.jpg")

    # Generate Val Normal (6 images)
    for i in range(6):
        img = create_sample_image(is_intruder=False, seed=200 + i)
        img.save(VAL_NORMAL / f"normal_val_{i:03d}.jpg")

    # Generate Val Intruder (6 images)
    for i in range(6):
        img = create_sample_image(is_intruder=True, seed=300 + i)
        img.save(VAL_INTRUDER / f"intruder_val_{i:03d}.jpg")

    print("[Dataset Generator] Done! Generated 40 training frames and 12 validation frames.")


if __name__ == "__main__":
    generate_all()
