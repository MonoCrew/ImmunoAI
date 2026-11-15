"""
================================================================================
 ImmunoAI — Google Colab GPU Training Script
 Copy-paste this entire script into a Google Colab notebook cell!
 
 Recommended Runtime: Free T4 GPU (Runtime -> Change runtime type -> T4 GPU)
================================================================================
"""

# ==============================================================================
# STEP 1: Install Kaggle & Download Dataset Directly in Colab
# ==============================================================================
"""
In a Google Colab cell, download the Kaggle dataset:

!pip install -q kagglehub
import kagglehub
path = kagglehub.dataset_download("hammadjavaid/person-classification-dataset")
print("Path to dataset files:", path)

# Or using Kaggle CLI (if you have kaggle.json):
# !mkdir -p ~/.kaggle && cp kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json
# !kaggle datasets download -d hammadjavaid/person-classification-dataset --unzip -p ./data
"""

import os
import time
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms
import matplotlib.pyplot as plt

# ==============================================================================
# STEP 2: The Exact ImmunoAICNN Architecture (Same as Local)
# ==============================================================================
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


# ==============================================================================
# STEP 3: Training Function
# ==============================================================================
def train_colab(data_dir: str, epochs: int = 25, batch_size: int = 32, lr: float = 0.001):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device] Using: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    # Image Transforms
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

    # Dataset Loader
    data_path = Path(data_dir)
    train_dir = data_path / "train"
    val_dir = data_path / "val" if (data_path / "val").exists() else (data_path / "test")

    if not val_dir.exists():
        # Auto-split single directory into 80/20 train/val
        full_ds = datasets.ImageFolder(str(data_path), transform=train_transform)
        train_size = int(0.8 * len(full_ds))
        val_size = len(full_ds) - train_size
        train_ds, val_ds = torch.utils.data.random_split(full_ds, [train_size, val_size])
    else:
        train_ds = datasets.ImageFolder(str(train_dir), transform=train_transform)
        val_ds = datasets.ImageFolder(str(val_dir), transform=val_transform)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2, pin_memory=True)

    print(f"[Data] Train: {len(train_ds)} samples | Val: {len(val_ds)} samples")

    model = ImmunoAICNN().to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

    best_val_loss = float("inf")
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []

    print("\nStarting Training on GPU...")
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
            # Save weights state dict
            torch.save(model.state_dict(), "immunoai_model.pth")

        elapsed = time.time() - epoch_start
        print(f"Epoch [{epoch:02d}/{epochs:02d}] "
              f"Train Loss: {epoch_train_loss:.4f} | Train Acc: {epoch_train_acc:.2f}% | "
              f"Val Loss: {epoch_val_loss:.4f} | Val Acc: {epoch_val_acc:.2f}% | "
              f"Time: {elapsed:.1f}s {'[BEST MODEL SAVED]' if is_best else ''}")

    total_time = time.time() - start_time
    print(f"\nTraining completed in {total_time/60:.2f} mins! Best Val Loss: {best_val_loss:.4f}")

    # Plot & Save Curves
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    epochs_range = range(1, epochs + 1)
    ax1.plot(epochs_range, train_losses, 'o-', color='#E88338', label='Train Loss')
    ax1.plot(epochs_range, val_losses, 's--', color='#22C55E', label='Val Loss')
    ax1.set_title('Binary Cross Entropy Loss')
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Loss')
    ax1.legend()
    ax1.grid(True, linestyle=':', alpha=0.6)

    ax2.plot(epochs_range, train_accs, 'o-', color='#3B82F6', label='Train Accuracy (%)')
    ax2.plot(epochs_range, val_accs, 's--', color='#10B981', label='Val Accuracy (%)')
    ax2.set_title('Detection Accuracy (%)')
    ax2.set_xlabel('Epochs')
    ax2.set_ylabel('Accuracy')
    ax2.legend()
    ax2.grid(True, linestyle=':', alpha=0.6)
    plt.tight_layout()
    plt.savefig("evaluation_curves.png", dpi=200)
    plt.show()

    # Automatic Download from Colab to local laptop
    try:
        from google.colab import files
        print("Downloading trained weights & evaluation curves to your computer...")
        files.download("immunoai_model.pth")
        files.download("evaluation_curves.png")
    except Exception:
        print("Files saved to current Colab workspace: immunoai_model.pth, evaluation_curves.png")


if __name__ == "__main__":
    # Example: replace './data' with the extracted dataset path from Kaggle
    train_colab(data_dir="./data", epochs=25, batch_size=32)
