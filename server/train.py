"""
ImmunoAI — Deep CNN Training & Evaluation Pipeline
Trains ImmunoAICNN on the dataset, tracks metrics, and exports loss curves and weights.

Run with:
  conda activate utility
  python server/train.py --data-dir server/data --epochs 15 --batch-size 32
"""

import argparse
import time
from pathlib import Path
import torch
import torch.nn as nn
import matplotlib.pyplot as plt

from model import ImmunoAICNN
from dataset import create_dataloaders
from config import MODEL_WEIGHTS_PATH, MODELS_DIR


def parse_args():
    parser = argparse.ArgumentParser(description="Train ImmunoAI Deep CNN for Intruder Detection")
    parser.add_argument("--data-dir", type=str, default="server/data", help="Path to dataset directory")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate for Adam optimizer")
    parser.add_argument("--output-weights", type=str, default=str(MODEL_WEIGHTS_PATH), help="Path to save best weights")
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

    all_preds = []
    all_targets = []

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

            all_preds.extend(predictions.cpu().squeeze().tolist())
            all_targets.extend(labels.cpu().squeeze().tolist())

    epoch_loss = running_loss / total
    epoch_acc = (correct / total) * 100.0
    return epoch_loss, epoch_acc, all_preds, all_targets


def plot_metrics(train_losses, val_losses, train_accs, val_accs, output_dir: Path):
    """
    Exports high-resolution training/validation curves for Viva presentation.
    """
    epochs_range = range(1, len(train_losses) + 1)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

    # Loss Curves
    ax1.plot(epochs_range, train_losses, label="Train Loss", color="#E88338", linewidth=2)
    ax1.plot(epochs_range, val_losses, label="Val Loss", color="#3B82F6", linewidth=2, linestyle="--")
    ax1.set_title("Training vs Validation Loss (Binary Cross-Entropy)", fontsize=13, fontweight="bold")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Accuracy Curves
    ax2.plot(epochs_range, train_accs, label="Train Accuracy", color="#22C55E", linewidth=2)
    ax2.plot(epochs_range, val_accs, label="Val Accuracy", color="#6366F1", linewidth=2, linestyle="--")
    ax2.set_title("Training vs Validation Accuracy (%)", fontsize=13, fontweight="bold")
    ax2.set_xlabel("Epoch")
    ax2.set_ylabel("Accuracy (%)")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    plt.tight_layout()
    chart_path = output_dir / "evaluation_curves.png"
    plt.savefig(chart_path, dpi=300)
    plt.close()
    print(f"[ImmunoAI] Saved evaluation curves to: {chart_path}")


def main():
    args = parse_args()
    data_dir = Path(args.data_dir)

    print("=" * 60)
    print(" ImmunoAI — Intruder Detection Deep CNN Trainer")
    print("=" * 60)

    if not data_dir.exists() or not any(data_dir.iterdir()):
        print(f"\n[Error] Dataset directory '{data_dir}' is empty or does not exist!")
        print("Please extract your dataset into:")
        print(f"  {data_dir.resolve()}/train/normal")
        print(f"  {data_dir.resolve()}/train/intruder")
        print("\nOnce you extract your dataset, re-run this command:")
        print(f"  conda activate utility")
        print(f"  python server/train.py --data-dir {args.data_dir}\n")
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

    # Plot & Save Evaluation Curves
    plot_metrics(train_losses, val_losses, train_accs, val_accs, MODELS_DIR)


if __name__ == "__main__":
    main()
