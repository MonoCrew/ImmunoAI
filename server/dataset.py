"""
ImmunoAI — Dataset Preparation, Preprocessing & Augmentation Pipeline
Handles loading image datasets for training and validation in PyTorch.
"""

from pathlib import Path
from typing import Tuple
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, transforms


def get_data_transforms(image_size: Tuple[int, int] = (224, 224)):
    """
    Returns data augmentation pipeline for training and clean transform for validation.
    Augmentations simulate lighting variations, camera tilt, and left/right entry directions.
    """
    train_transforms = transforms.Compose([
        transforms.Resize(image_size),
        transforms.RandomHorizontalFlip(p=0.5),          # Handles intruder entering from left or right
        transforms.RandomRotation(degrees=10),           # Small camera angle jitter
        transforms.ColorJitter(brightness=0.2, contrast=0.2), # Day/night and indoor lighting variations
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    val_transforms = transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )
    ])

    return train_transforms, val_transforms


def create_dataloaders(
    data_dir: str,
    batch_size: int = 32,
    image_size: Tuple[int, int] = (224, 224),
    val_split: float = 0.2,
    num_workers: int = 2
) -> Tuple[DataLoader, DataLoader, dict]:
    """
    Scans data directory. Supports:
      1) data_dir/train and data_dir/val subdirectories
      2) Or single data_dir with class folders (auto-splits train/val by val_split ratio)
    """
    path = Path(data_dir)
    train_transforms, val_transforms = get_data_transforms(image_size)

    # Check for separate train/val structure
    has_train_val = (path / "train").exists() and (path / "val").exists()

    if has_train_val:
        train_dataset = datasets.ImageFolder(root=str(path / "train"), transform=train_transforms)
        val_dataset = datasets.ImageFolder(root=str(path / "val"), transform=val_transforms)
        class_to_idx = train_dataset.class_to_idx
    else:
        # Single directory with class folders: auto-split
        full_dataset = datasets.ImageFolder(root=str(path), transform=train_transforms)
        class_to_idx = full_dataset.class_to_idx

        val_size = int(len(full_dataset) * val_split)
        train_size = len(full_dataset) - val_size

        train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    info = {
        "num_train_samples": len(train_dataset),
        "num_val_samples": len(val_dataset),
        "class_to_idx": class_to_idx,
        "classes": list(class_to_idx.keys())
    }

    return train_loader, val_loader, info
