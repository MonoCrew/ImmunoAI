"""
ImmunoAI — Deep CNN Training & Evaluation Pipeline
Trains ImmunoAICNN on the dataset, tracks metrics, and exports loss curves and weights.

Run with:
  conda activate utility
  cd server/ai_service/training_model
  python train.py --epochs 25 --batch-size 32
"""

import argparse
import time
from pathlib import Path
import torch
import torch.nn as nn
import matplotlib.pyplot as plt

from model import ImmunoAICNN
from dataset import create_dataloaders

# Self-contained paths pointing to ai_service/data and ai_service/saved_model
BASE_DIR = Path(__file__).resolve().parent
SAVED_MODEL_DIR = BASE_DIR.parent / "saved_model"
SAVED_MODEL_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_DATA_DIR = BASE_DIR.parent / "data"
DEFAULT_WEIGHTS_PATH = SAVED_MODEL_DIR / "immunoai_model.pth"


def parse_args():
    parser = argparse.ArgumentParser(description="Train ImmunoAI Deep CNN for Intruder Detection")
    parser.add_argument("--data-dir", type=str, default=str(DEFAULT_DATA_DIR), help="Path to dataset directory")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate for Adam optimizer")
    parser.add_argument("--output-weights", type=str, default=str(DEFAULT_WEIGHTS_PATH), help="Path to save best weights")
    return parser.parse_args()


def train_one_epoch(model, dataloader, criterion, optimizer, device):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in dataloader:
        images = images.to(device)
        labels = labels.to(device).float().unsqueeze(1)  # (Batch, 1)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        predictions = (torch.sigmoid(outputs) >= 0.5).float()
        correct += (predictions == labels).sum().item()
        total += labels.size(0)

    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100.0
    return epoch_loss, epoch_acc


def validate(model, dataloader, criterion, device):
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds, all_targets = [], []

    with torch.no_grad():
        for images, labels in dataloader:
            images = images.to(device)
            labels = labels.to(device).float().unsqueeze(1)

            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            predictions = (torch.sigmoid(outputs) >= 0.5).float()
            correct += (predictions == labels).sum().item()
            total += labels.size(0)

            all_preds.extend(predictions.cpu().numpy().flatten())
            all_targets.extend(labels.cpu().numpy().flatten())

    val_loss = running_loss / total
    val_acc = (correct / total) * 100.0
    return val_loss, val_acc, all_preds, all_targets


def plot_metrics(train_losses, val_losses, train_accs, val_accs, output_dir: Path):
    """Generates and saves the loss and accuracy evaluation curves"""
    epochs = range(1, len(train_losses) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Loss plot
    ax1.plot(epochs, train_losses, 'o-', color='#E88338', label='Training Loss', linewidth=2)
    ax1.plot(epochs, val_losses, 's--', color='#22C55E', label='Validation Loss', linewidth=2)
    ax1.set_title('ImmunoAI — Binary Cross Entropy Loss', fontsize=12, fontweight='bold')
    ax1.set_xlabel('Epochs')
    ax1.set_ylabel('Loss')
    ax1.grid(True, linestyle=':', alpha=0.6)
    ax1.legend()

    # Accuracy plot
    ax2.plot(epochs, train_accs, 'o-', color='#3B82F6', label='Training Accuracy (%)', linewidth=2)
    ax2.plot(epochs, val_accs, 's--', color='#10B981', label='Validation Accuracy (%)', linewidth=2)
    ax2.set_title('ImmunoAI — Detection Accuracy (%)', fontsize=12, fontweight='bold')
    ax2.set_xlabel('Epochs')
    ax2.set_ylabel('Accuracy (%)')
    ax2.set_ylim([0, 105])
    ax2.grid(True, linestyle=':', alpha=0.6)
    ax2.legend()

    plt.tight_layout()
    curve_path = output_dir / "evaluation_curves.png"
    plt.savefig(str(curve_path), dpi=200)
    plt.close()
    print(f"[ImmunoAI] Saved evaluation curves to: {curve_path.resolve()}")


def main():
    args = parse_args()
    print("=" * 60)
    print(" ImmunoAI — Intruder Detection Deep CNN Trainer")
    print("=" * 60)

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"[Error] Dataset directory '{data_dir.resolve()}' not found.")
        print("Please extract your dataset into:")
        print(f"  {data_dir.resolve()}/train/normal")
        print(f"  {data_dir.resolve()}/train/intruder")
        return

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[Device] Using: {device} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'})")

    print(f"[Data] Loading dataset from: {data_dir.resolve()}")
    train_loader, val_loader, info = create_dataloaders(
        data_dir=str(data_dir),
        batch_size=args.batch_size
    )

    print(f"[Data] Train samples: {info['num_train_samples']} | Validation samples: {info['num_val_samples']}")
    print(f"[Data] Classes detected: {info['classes']} -> {info['class_to_idx']}")

    # Model, Loss, Optimizer
    model = ImmunoAICNN(num_classes=1).to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=2, factor=0.5)

    best_val_loss = float("inf")
    output_weights = Path(args.output_weights)
    output_weights.parent.mkdir(parents=True, exist_ok=True)

    train_losses, val_losses = [], []
    train_accs, val_accs = [], []

    print("\nStarting Training Loop...")
    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        epoch_start = time.time()

        train_loss, train_acc = train_one_epoch(model, train_loader, criterion, optimizer, device)
        val_loss, val_acc, preds, targets = validate(model, val_loader, criterion, device)
        scheduler.step(val_loss)

        train_losses.append(train_loss)
        val_losses.append(val_loss)
        train_accs.append(train_acc)
        val_accs.append(val_acc)

        elapsed = time.time() - epoch_start
        is_best = val_loss < best_val_loss

        print(
            f"Epoch [{epoch:02d}/{args.epochs:02d}] "
            f"Train Loss: {train_loss:.4f} | Train Acc: {train_acc:.2f}% | "
            f"Val Loss: {val_loss:.4f} | Val Acc: {val_acc:.2f}% | "
            f"Time: {elapsed:.1f}s"
            f"{' -> [Saved Best Model]' if is_best else ''}"
        )

        if is_best:
            best_val_loss = val_loss
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "val_acc": val_acc,
                "val_loss": val_loss,
                "class_to_idx": info["class_to_idx"]
            }, str(output_weights))

    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print(f" Training Complete in {total_time/60:.2f} minutes!")
    print(f" Best Validation Loss: {best_val_loss:.4f}")
    print(f" Best Weights Saved to: {output_weights.resolve()}")
    print("=" * 60)

    # Plot & Save Evaluation Curves to saved_model/
    plot_metrics(train_losses, val_losses, train_accs, val_accs, output_weights.parent)


if __name__ == "__main__":
    main()
