"""
ImmunoAI — Custom Deep Convolutional Neural Network (CNN) Architecture
Designed for Real-Time Intruder Detection in PyTorch.

Architecture Hierarchy:
  - Input: (Batch, 3, 224, 224) RGB Image
  - Conv Block 1: Low-level edge & gradient extraction (3 -> 32 channels)
  - Conv Block 2: Intermediate textures & geometric patterns (32 -> 64 channels)
  - Conv Block 3: Human body contours & silhouette features (64 -> 128 channels)
  - Conv Block 4: High-level semantic intrusion patterns (128 -> 256 channels)
  - AdaptiveAvgPool2d: Spatial pooling to 1x1 (input-size invariant)
  - Dense Classifier Head: Dropout(0.4) -> Linear(256, 64) -> ReLU -> Linear(64, 1) Logit Output
"""

import torch
import torch.nn as nn
from pathlib import Path


class ConvBlock(nn.Module):
    """
    Standard Convolutional Block:
    Conv2D (3x3 kernel, padding 1) -> Batch Normalization -> ReLU -> Max Pooling (2x2)
    """
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
    """
    Deep CNN for Intruder Detection.
    Outputs a single logit representing P(Intruder) via Binary Cross-Entropy Loss.
    """
    def __init__(self, num_classes: int = 1):
        super(ImmunoAICNN, self).__init__()

        # Feature Extraction Backbone (4 Hierarchical Convolutional Blocks)
        self.features = nn.Sequential(
            ConvBlock(in_channels=3, out_channels=32),    # 224x224 -> 112x112
            ConvBlock(in_channels=32, out_channels=64),   # 112x112 -> 56x56
            ConvBlock(in_channels=64, out_channels=128),  # 56x56 -> 28x28
            ConvBlock(in_channels=128, out_channels=256), # 28x28 -> 14x14
        )

        # Global Adaptive Average Pooling (Reduces spatial dimensions from 14x14 to 1x1)
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))

        # Classification Head (Regularized with Dropout to prevent overfitting)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(p=0.4),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(p=0.2),
            nn.Linear(64, num_classes)  # 1 logit output (0: Normal, 1: Intruder)
        )

        # Weight Initialization using Kaiming (He) Normal
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


def get_model(weights_path: str = None, device: str = "cpu") -> ImmunoAICNN:
    """
    Factory function to instantiate ImmunoAICNN and optionally load trained weights.
    """
    model = ImmunoAICNN()
    if weights_path and Path(weights_path).exists():
        checkpoint = torch.load(weights_path, map_location=device)
        if isinstance(checkpoint, dict) and "state_dict" in checkpoint:
            model.load_state_dict(checkpoint["state_dict"])
        elif isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
            model.load_state_dict(checkpoint["model_state_dict"])
        else:
            model.load_state_dict(checkpoint)
        print(f"[ImmunoAI] Loaded trained model weights from: {weights_path}")
    else:
        print("[ImmunoAI] Initialized fresh ImmunoAICNN model.")

    model.to(device)
    model.eval()
    return model


if __name__ == "__main__":
    # Test shape & forward pass
    dummy_input = torch.randn(2, 3, 224, 224)
    model = ImmunoAICNN()
    output = model(dummy_input)
    print("ImmunoAICNN successfully compiled!")
    print(f"Input shape:  {dummy_input.shape}")
    print(f"Output shape: {output.shape} (Logits for batch size 2)")
    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total Trainable Parameters: {total_params:,}")
