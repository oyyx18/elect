"""Object detection task (YOLO by default, local dataset in YOLO format)."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable, List, Tuple

import torch
from PIL import Image as PilImage
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision.transforms import Compose, ToTensor

DEFAULT_DATASET_ROOT = Path(os.getenv("YOLO_DATASET_ROOT", "./data/yolo"))
DEFAULT_MODEL_NAME = "yolov8n"
SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")


@dataclass
class YoloSample:
    image: torch.Tensor
    boxes: torch.Tensor
    labels: torch.Tensor


class YoloFormatDataset(Dataset):
    """Read a local dataset in YOLO format.

    Expected structure:
    - {root}/images/{split}/*.jpg|png
    - {root}/labels/{split}/*.txt (class x_center y_center width height, normalized)
    """

    def __init__(self, dataset_root: Path, split: str, transforms=None) -> None:
        self.dataset_root = Path(dataset_root)
        self.split = split
        self.transforms = transforms or Compose([ToTensor()])

        self.image_dir = self.dataset_root / "images" / split
        self.label_dir = self.dataset_root / "labels" / split

        self.image_paths = sorted(
            [
                path
                for path in self.image_dir.rglob("*")
                if path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
            ]
        )
        if not self.image_paths:
            raise FileNotFoundError(f"No images found under {self.image_dir}")

    def __len__(self) -> int:
        return len(self.image_paths)

    def __getitem__(self, index: int) -> dict:
        image_path = self.image_paths[index]
        label_path = self.label_dir / f"{image_path.stem}.txt"

        image = PilImage.open(image_path).convert("RGB")
        width, height = image.size

        boxes, labels = _read_yolo_labels(label_path, width, height)
        sample = {
            "img": self.transforms(image),
            "boxes": boxes,
            "labels": labels,
        }
        return sample


def _read_yolo_labels(label_path: Path, width: int, height: int) -> Tuple[torch.Tensor, torch.Tensor]:
    if not label_path.exists():
        return torch.zeros((0, 4), dtype=torch.float32), torch.zeros((0,), dtype=torch.int64)

    boxes: List[List[float]] = []
    labels: List[int] = []
    with label_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            raw = raw.strip()
            if not raw:
                continue
            parts = raw.split()
            if len(parts) != 5:
                raise ValueError(f"Invalid label row in {label_path}: {raw}")
            class_id, x_center, y_center, w_norm, h_norm = parts
            x_center = float(x_center) * width
            y_center = float(y_center) * height
            box_width = float(w_norm) * width
            box_height = float(h_norm) * height

            x_min = x_center - box_width / 2.0
            y_min = y_center - box_height / 2.0
            x_max = x_center + box_width / 2.0
            y_max = y_center + box_height / 2.0

            boxes.append([x_min, y_min, x_max, y_max])
            labels.append(int(class_id))

    return torch.tensor(boxes, dtype=torch.float32), torch.tensor(labels, dtype=torch.int64)


def _partition_indices(num_samples: int, partition_id: int, num_partitions: int) -> List[int]:
    if num_partitions <= 0:
        raise ValueError("num_partitions must be > 0")
    if not (0 <= partition_id < num_partitions):
        raise ValueError("partition_id must be within [0, num_partitions)")

    indices = list(range(num_samples))
    partition_size = num_samples // num_partitions
    remainder = num_samples % num_partitions

    start = partition_id * partition_size + min(partition_id, remainder)
    end = start + partition_size + (1 if partition_id < remainder else 0)
    return indices[start:end]


def _collate_detection(batch: Iterable[dict]):
    images = [item["img"] for item in batch]
    targets = [
        {
            "boxes": item["boxes"],
            "labels": item["labels"],
        }
        for item in batch
    ]
    return images, targets


class YoloWrapper(torch.nn.Module):
    """Thin wrapper around Ultralytics YOLO to expose a torch.nn.Module."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, weights_path: str | None = None) -> None:
        super().__init__()
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Ultralytics YOLO is required for detection. "
                "Install with `pip install ultralytics`."
            ) from exc

        model_path = weights_path or f"{model_name}.pt"
        self.yolo = YOLO(model_path)
        self.model = self.yolo.model

    def forward(self, x: torch.Tensor):
        return self.model(x)


def Net(model_name: str = DEFAULT_MODEL_NAME) -> torch.nn.Module:
    """Build a YOLO model (via Ultralytics) by default."""

    return YoloWrapper(model_name=model_name)


def load_data(partition_id: int, num_partitions: int, batch_size: int, dataset_root: Path = DEFAULT_DATASET_ROOT):
    """Load a local YOLO-format dataset and return train/val dataloaders."""

    train_dataset = YoloFormatDataset(dataset_root=Path(dataset_root), split="train")
    val_dataset = YoloFormatDataset(dataset_root=Path(dataset_root), split="val")

    partition_indices = _partition_indices(len(train_dataset), partition_id, num_partitions)
    partition_dataset = Subset(train_dataset, partition_indices)

    trainloader = DataLoader(
        partition_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=_collate_detection,
    )
    valloader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        collate_fn=_collate_detection,
    )

    return trainloader, valloader


def load_centralized_dataset(dataset_root: Path = DEFAULT_DATASET_ROOT) -> DataLoader:
    """Load the local YOLO-format validation dataset for centralized eval."""

    val_dataset = YoloFormatDataset(dataset_root=Path(dataset_root), split="val")
    return DataLoader(val_dataset, batch_size=4, shuffle=False, collate_fn=_collate_detection)


def train(net: torch.nn.Module, trainloader: DataLoader, epochs: int, lr: float, device: torch.device):
    """Train a YOLO model using Ultralytics."""

    if not isinstance(net, YoloWrapper):
        raise TypeError("Detection training expects a YoloWrapper model.")

    dataset_root = _get_dataset_root(trainloader.dataset)
    data_yaml = _ensure_yolo_dataset_yaml(Path(dataset_root))

    results = net.yolo.train(
        data=str(data_yaml),
        epochs=epochs,
        lr0=lr,
        device=str(device),
    )

    loss = 0.0
    if hasattr(results, "results_dict"):
        loss = float(results.results_dict.get("train/box_loss", 0.0))
    return loss


def test(net: torch.nn.Module, testloader: DataLoader, device: torch.device):
    """Evaluate a YOLO model using Ultralytics and return (loss, mAP50)."""

    if not isinstance(net, YoloWrapper):
        raise TypeError("Detection evaluation expects a YoloWrapper model.")

    dataset_root = _get_dataset_root(testloader.dataset)
    data_yaml = _ensure_yolo_dataset_yaml(Path(dataset_root))

    results = net.yolo.val(data=str(data_yaml), device=str(device))

    loss = 0.0
    map50 = 0.0
    if hasattr(results, "results_dict"):
        loss = float(results.results_dict.get("val/box_loss", 0.0))
        map50 = float(results.results_dict.get("metrics/mAP50", 0.0))
    return loss, map50


def _ensure_yolo_dataset_yaml(dataset_root: Path) -> Path:
    """Create a minimal YOLO dataset YAML alongside the dataset if missing."""

    yaml_path = dataset_root / "dataset.yaml"
    if yaml_path.exists():
        return yaml_path

    train_path = (dataset_root / "images" / "train").resolve()
    val_path = (dataset_root / "images" / "val").resolve()

    yaml_content = "\n".join(
        [
            f"path: {dataset_root.resolve()}",
            f"train: {train_path}",
            f"val: {val_path}",
            "names: []",
            "",
        ]
    )
    yaml_path.write_text(yaml_content, encoding="utf-8")
    return yaml_path


def _get_dataset_root(dataset) -> Path:
    if hasattr(dataset, "dataset_root"):
        return Path(dataset.dataset_root)
    if isinstance(dataset, Subset):
        return _get_dataset_root(dataset.dataset)
    return DEFAULT_DATASET_ROOT



def train(net: torch.nn.Module, trainloader: DataLoader, epochs: int, lr: float, device: torch.device):
    """Train a YOLO model using Ultralytics."""

    if not isinstance(net, YoloWrapper):
        raise TypeError("Detection training expects a YoloWrapper model.")

    dataset_root = _get_dataset_root(trainloader.dataset)
    data_yaml = _ensure_yolo_dataset_yaml(Path(dataset_root))

    results = net.yolo.train(
        data=str(data_yaml),
        epochs=epochs,
        lr0=lr,
        device=str(device),
    )

    loss = 0.0
    if hasattr(results, "results_dict"):
        loss = float(results.results_dict.get("train/box_loss", 0.0))
    return loss


def test(net: torch.nn.Module, testloader: DataLoader, device: torch.device):
    """Evaluate a YOLO model using Ultralytics and return (loss, mAP50)."""

    if not isinstance(net, YoloWrapper):
        raise TypeError("Detection evaluation expects a YoloWrapper model.")

    dataset_root = _get_dataset_root(testloader.dataset)
    data_yaml = _ensure_yolo_dataset_yaml(Path(dataset_root))

    results = net.yolo.val(data=str(data_yaml), device=str(device))

    loss = 0.0
    map50 = 0.0
    if hasattr(results, "results_dict"):
        loss = float(results.results_dict.get("val/box_loss", 0.0))
        map50 = float(results.results_dict.get("metrics/mAP50", 0.0))
    return loss, map50


def _ensure_yolo_dataset_yaml(dataset_root: Path) -> Path:
    """Create a minimal YOLO dataset YAML alongside the dataset if missing."""

    yaml_path = dataset_root / "dataset.yaml"
    if yaml_path.exists():
        return yaml_path

    train_path = (dataset_root / "images" / "train").resolve()
    val_path = (dataset_root / "images" / "val").resolve()

    yaml_content = "\n".join(
        [
            f"path: {dataset_root.resolve()}",
            f"train: {train_path}",
            f"val: {val_path}",
            "names: []",
            "",
        ]
    )
    yaml_path.write_text(yaml_content, encoding="utf-8")
    return yaml_path


def _get_dataset_root(dataset) -> Path:
    if hasattr(dataset, "dataset_root"):
        return Path(dataset.dataset_root)
    if isinstance(dataset, Subset):
        return _get_dataset_root(dataset.dataset)
    return DEFAULT_DATASET_ROOT
