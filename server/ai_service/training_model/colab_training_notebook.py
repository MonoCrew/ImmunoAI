"""
================================================================================
 ImmunoAI — Google Colab MS COCO Person Dataset Training Pipeline
 
 Extracts 5,000 real MS COCO images (Person vs Non-Person background)
 and trains the ImmunoAICNN Deep Learning model on GPU!
 
 Runtime: Google Colab Free T4 GPU (Runtime -> Change runtime type -> T4 GPU)
 Total Execution Time: ~6 to 8 minutes
================================================================================
"""

# ==============================================================================
# CELL 1: Download Official MS COCO Subset & Extract Person vs Background
# (Run this directly in Google Colab — downloads in ~20 seconds from AWS S3)
# ==============================================================================
"""
# Run in Colab:
!pip install -q pycocotools

import os
import shutil
from pycocotools.coco import COCO

# 1. Download MS COCO 2017 (Val images 1GB + Annotations 240MB)
!wget -c -q --show-progress http://images.cocodataset.org/zips/val2017.zip
!wget -c -q --show-progress http://images.cocodataset.org/annotations/annotations_trainval2017.zip

!unzip -q -o val2017.zip
!unzip -q -o annotations_trainval2017.zip

# 2. Parse COCO annotations to extract Person (Class 1) vs Non-Person Background (Class 0)
coco = COCO('annotations/instances_val2017.json')
person_cat_id = coco.getCatIds(catNms=['person'])[0]
person_img_ids = set(coco.getImgIds(catIds=[person_cat_id]))

DATA_DIR = './coco_person_data'
os.makedirs(f'{DATA_DIR}/train/normal', exist_ok=True)
os.makedirs(f'{DATA_DIR}/train/person', exist_ok=True)
os.makedirs(f'{DATA_DIR}/val/normal', exist_ok=True)
os.makedirs(f'{DATA_DIR}/val/person', exist_ok=True)

print("Filtering MS COCO images into balanced Person vs Normal classes...")
person_count = 0
normal_count = 0

for img_id, info in coco.imgs.items():
    fname = info['file_name']
    src_path = os.path.join('val2017', fname)
    if not os.path.exists(src_path):
        continue

    is_person = img_id in person_img_ids
    # 80% train / 20% validation split based on image ID
    split = 'val' if (img_id % 5 == 0) else 'train'

    if is_person:
        dst = f'{DATA_DIR}/{split}/person/{fname}'
        shutil.copy(src_path, dst)
        person_count += 1
    else:
        # Keep dataset balanced: match person count
        if normal_count < 2600:
            dst = f'{DATA_DIR}/{split}/normal/{fname}'
            shutil.copy(src_path, dst)
            normal_count += 1

print(f"Dataset Prepared: {person_count} Person images, {normal_count} Normal background images.")
"""

# ==============================================================================
# CELL 2: PyTorch Model Definition, Training & Automatic Weight Download
# ==============================================================================
import os
import time
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt


# ------------------------------------------------------------------------------
# 1. ImmunoAICNN Architecture (100% Identical to Local Inference Model)
# ------------------------------------------------------------------------------
class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super(ConvBlock, self).__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class ImmunoAICNN(nn.Module):
    def __init__(self, num_classes: int = 1):
        super(ImmunoAICNN, self).__init__()
        self.features = nn.Sequential(
            ConvBlock(in_channels=3, out_channels=32),
            ConvBlock(in_channels=32, out_channels=64),
            ConvBlock(in_channels=64, out_channels=128),
            ConvBlock(in_channels=128, out_channels=256),
        )
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.4),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(64, num_classes)
        )
        self._initialize_weights()

    def _initialize_weights(self):
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.kaiming_uniform_(m.weight, nonlinearity='relu')
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = self.features(x)
        x = self.global_pool(x)
        logits = self.classifier(x)
        return logits


# ------------------------------------------------------------------------------
# 2. Training Function on GPU
# ------------------------------------------------------------------------------
def train_coco_person(data_dir: str = "./coco_person_data", epochs: int = 20, batch_size: int = 32, lr: float = 0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n[ImmunoAI Training] Using Device: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # Image Transforms (Standard ImageNet Normalization)
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    train_ds = datasets.ImageFolder(f"{data_dir}/train", transform=train_transform)
    val_ds = datasets.ImageFolder(f"{data_dir}/val", transform=val_transform)

    # In alphabetical sorting: 'normal' -> 0 (negative), 'person' -> 1 (positive intruder)
    print(f"[Class Mapping] {train_ds.class_to_idx} (0 = Normal Background, 1 = Person Intruder)")
    print(f"[Data Split] Train: {len(train_ds)} samples | Val: {len(val_ds)} samples\n")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)

    model = ImmunoAICNN(num_classes=1).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

    best_val_loss = float("inf")
    best_val_acc = 0.0
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []

    print("=" * 65)
    print(" Starting MS COCO Person Model Training...")
    print("=" * 65)
    start_time = time.time()

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()

        # Training Phase
        model.train()
        train_loss, train_correct, train_total = 0.0, 0, 0
        for imgs, lbls in train_loader:
            imgs, lbls = imgs.to(device), lbls.to(device).float().unsqueeze(1)
            optimizer.zero_grad()
            outs = model(imgs)
            loss = criterion(outs, lbls)
            loss.backward()
            optimizer.step()

            train_loss += loss.item() * imgs.size(0)
            preds = (torch.sigmoid(outs) >= 0.5).float()
            train_correct += (preds == lbls).sum().item()
            train_total += lbls.size(0)

        epoch_train_loss = train_loss / train_total
        epoch_train_acc = (train_correct / train_total) * 100.0

        # Validation Phase
        model.eval()
        val_loss, val_correct, val_total = 0.0, 0, 0
        with torch.no_grad():
            for imgs, lbls in val_loader:
                imgs, lbls = imgs.to(device), lbls.to(device).float().unsqueeze(1)
                outs = model(imgs)
                loss = criterion(outs, lbls)
                val_loss += loss.item() * imgs.size(0)
                preds = (torch.sigmoid(outs) >= 0.5).float()
                val_correct += (preds == lbls).sum().item()
                val_total += lbls.size(0)

        epoch_val_loss = val_loss / val_total
        epoch_val_acc = (val_correct / val_total) * 100.0

        scheduler.step(epoch_val_loss)

        train_losses.append(epoch_train_loss)
        val_losses.append(epoch_val_loss)
        train_accs.append(epoch_train_acc)
        val_accs.append(epoch_val_acc)

        is_best = epoch_val_loss < best_val_loss
        if is_best:
            best_val_loss = epoch_val_loss
            best_val_acc = epoch_val_acc
            # Save the best model checkpoint
            torch.save(model.state_dict(), "immunoai_model.pth")

        elapsed = time.time() - epoch_start
        print(f"Epoch [{epoch:02d}/{epochs:02d}] "
              f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:5.2f}% | "
              f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc:5.2f}% | "
              f"Time: {elapsed:4.1f}s {'[BEST MODEL SAVED ⭐]' if is_best else ''}")

    total_time = time.time() - start_time
    print("=" * 65)
    print(f"Training Complete in {total_time/60:.2f} mins! Best Val Acc: {best_val_acc:.2f}% | Best Val Loss: {best_val_loss:.4f}")
    print("=" * 65)

    # Plot & Save Evaluation Curves for Viva Presentation
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    epochs_range = range(1, epochs + 1)
    ax1.plot(epochs_range, train_losses, 'o-', color='#E88338', label='Train Loss', linewidth=2)
    ax1.plot(epochs_range, val_losses, 's--', color='#22C55E', label='Val Loss', linewidth=2)
    ax1.set_title('Binary Cross Entropy Loss (MS COCO Person)', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2.plot(epochs_range, train_accs, 'o-', color='#3B82F6', label='Train Accuracy (%)', linewidth=2)
    ax2.plot(epochs_range, val_accs, 's--', color='#10B981', label='Val Accuracy (%)', linewidth=2)
    ax2.set_title('Intruder Detection Accuracy (%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Epochs')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_ylim([0, 105])
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig("evaluation_curves.png", dpi=200)
    plt.show()

    # Automatically trigger download of trained model & graphs to your laptop
    try:
        from google.colab import files
        print("\n⬇️ Downloading immunoai_model.pth and evaluation_curves.png to your laptop...")
        files.download("immunoai_model.pth")
        files.download("evaluation_curves.png")
    except Exception:
        print("\nFiles saved in Colab workspace: immunoai_model.pth, evaluation_curves.png")


if __name__ == "__main__":
    train_coco_person(data_dir="./coco_person_data", epochs=20, batch_size=32, lr=0.001)
