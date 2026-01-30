"""Object detection task (YOLO by default, local dataset in YOLO format)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

try:
    import tomllib
except ImportError:  # Python < 3.11
    import tomli as tomllib

import torch
from PIL import Image as PilImage
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision.transforms import Compose, ToTensor
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT_TOML = PROJECT_ROOT / "pyproject.toml"

DEFAULT_MODEL_NAME = "yolov8n"
SUPPORTED_IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")
METRIC_NAME = "map50"


@dataclass
class YoloSample:
    image: torch.Tensor
    boxes: torch.Tensor
    labels: torch.Tensor


class YoloFormatDataset(Dataset):
    """Read a local dataset in YOLO format using resolved image/label directories."""

    def __init__(
        self,
        dataset_root: Path,
        image_dir: Path,
        label_dir: Path,
        dataset_yaml: Path,
        transforms=None,
    ) -> None:
        self.dataset_root = Path(dataset_root)
        self.dataset_yaml = Path(dataset_yaml)
        self.image_dir = Path(image_dir)
        self.label_dir = Path(label_dir)
        self.transforms = transforms or Compose([ToTensor()])

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


def _load_app_config() -> dict:
    if not PYPROJECT_TOML.exists():
        raise FileNotFoundError(f"Missing {PYPROJECT_TOML}")
    with PYPROJECT_TOML.open("rb") as handle:
        data = tomllib.load(handle)
    return (
        data.get("tool", {})
        .get("flwr", {})
        .get("app", {})
        .get("config", {})
    )


def _resolve_dataset_yaml_path(app_config: dict) -> Path:
    dataset_name = app_config.get("dataset-name") or app_config.get("dataset_name")
    if not dataset_name:
        raise ValueError("Missing dataset-name in [tool.flwr.app.config] of pyproject.toml")
    dataset_root = PROJECT_ROOT / "allDatasets" / str(dataset_name)
    data_yaml = dataset_root / "data.yaml"
    if not data_yaml.exists():
        raise FileNotFoundError(f"Missing YOLO data.yaml at {data_yaml}")
    return data_yaml


def _load_yolo_data_yaml(data_yaml: Path) -> dict:
    with data_yaml.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid YOLO data.yaml at {data_yaml}")
    return data


def _resolve_dataset_root(
    data_yaml: Path, yolo_data: dict, dataset_root_override: Path | None = None
) -> Path:
    if dataset_root_override is not None:
        return Path(dataset_root_override)

    raw_path = yolo_data.get("path")
    if not raw_path:
        return data_yaml.parent

    path_value = Path(str(raw_path))
    if path_value.is_absolute():
        return path_value

    # Prefer resolving relative paths from the data.yaml location (YOLO convention).
    yaml_candidate = (data_yaml.parent / path_value).resolve()
    if yaml_candidate.exists():
        return yaml_candidate

    project_candidate = (PROJECT_ROOT / path_value).resolve()
    if project_candidate.exists():
        return project_candidate

    return yaml_candidate


def _labels_dir_from_images_dir(images_dir: Path) -> Path:
    parts = list(images_dir.parts)
    if "images" in parts:
        index = len(parts) - 1 - parts[::-1].index("images")
        parts[index] = "labels"
        return Path(*parts)
    return images_dir.parent / "labels"


def _resolve_split_paths(dataset_root: Path, yolo_data: dict) -> dict[str, Tuple[Path, Path]]:
    split_paths: dict[str, Tuple[Path, Path]] = {}

    val_key = "val" if "val" in yolo_data else "valid" if "valid" in yolo_data else None
    split_keys = {
        "train": yolo_data.get("train"),
        "val": yolo_data.get(val_key) if val_key else None,
        "test": yolo_data.get("test"),
    }

    for split, value in split_keys.items():
        if not value:
            continue
        raw_path = Path(str(value))
        image_dir = raw_path if raw_path.is_absolute() else (dataset_root / raw_path).resolve()
        label_dir = _labels_dir_from_images_dir(image_dir)
        split_paths[split] = (image_dir, label_dir)

    return split_paths


def _resolve_yolo_dataset(dataset_root: Path | None = None) -> Tuple[Path, Path, dict[str, Tuple[Path, Path]]]:
    app_config = _load_app_config()
    data_yaml = _resolve_dataset_yaml_path(app_config)
    yolo_data = _load_yolo_data_yaml(data_yaml)
    root = _resolve_dataset_root(data_yaml, yolo_data, dataset_root_override=dataset_root)
    split_paths = _resolve_split_paths(root, yolo_data)
    return data_yaml, root, split_paths


def _write_resolved_yolo_yaml(dataset_root: Path | None = None) -> Path:
    data_yaml, resolved_root, split_paths = _resolve_yolo_dataset(dataset_root)
    yolo_data = _load_yolo_data_yaml(data_yaml)

    resolved_data = dict(yolo_data)
    resolved_data["path"] = str(resolved_root)
    if "train" in split_paths:
        resolved_data["train"] = str(split_paths["train"][0])
    if "val" in split_paths:
        resolved_data["val"] = str(split_paths["val"][0])
    if "test" in split_paths:
        resolved_data["test"] = str(split_paths["test"][0])

    resolved_yaml = data_yaml.parent / ".resolved_data.yaml"
    with resolved_yaml.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(resolved_data, handle, allow_unicode=True, sort_keys=False)
    return resolved_yaml


def load_data(
    partition_id: int,
    num_partitions: int,
    batch_size: int,
    dataset_root: Path | None = None,
):
    """Load a local YOLO-format dataset and return train/val dataloaders."""

    data_yaml, resolved_root, split_paths = _resolve_yolo_dataset(dataset_root)
    if "train" not in split_paths or "val" not in split_paths:
        raise ValueError("YOLO data.yaml must define both train and val image paths.")

    train_image_dir, train_label_dir = split_paths["train"]
    val_image_dir, val_label_dir = split_paths["val"]

    train_dataset = YoloFormatDataset(
        dataset_root=resolved_root,
        image_dir=train_image_dir,
        label_dir=train_label_dir,
        dataset_yaml=data_yaml,
    )
    val_dataset = YoloFormatDataset(
        dataset_root=resolved_root,
        image_dir=val_image_dir,
        label_dir=val_label_dir,
        dataset_yaml=data_yaml,
    )

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


def load_centralized_dataset(dataset_root: Path | None = None) -> DataLoader:
    """Load the local YOLO-format validation dataset for centralized eval."""

    data_yaml, resolved_root, split_paths = _resolve_yolo_dataset(dataset_root)
    if "val" not in split_paths:
        raise ValueError("YOLO data.yaml must define a val image path.")

    val_image_dir, val_label_dir = split_paths["val"]
    val_dataset = YoloFormatDataset(
        dataset_root=resolved_root,
        image_dir=val_image_dir,
        label_dir=val_label_dir,
        dataset_yaml=data_yaml,
    )
    return DataLoader(val_dataset, batch_size=4, shuffle=False, collate_fn=_collate_detection)


def _get_dataset_root(dataset) -> Path:
    if hasattr(dataset, "dataset_root"):
        return Path(dataset.dataset_root)
    if isinstance(dataset, Subset):
        return _get_dataset_root(dataset.dataset)
    _, root, _ = _resolve_yolo_dataset()
    return root


def _get_dataset_yaml(dataset) -> Path:
    if hasattr(dataset, "dataset_yaml"):
        return Path(dataset.dataset_yaml)
    if isinstance(dataset, Subset):
        return _get_dataset_yaml(dataset.dataset)
    app_config = _load_app_config()
    return _resolve_dataset_yaml_path(app_config)


def train(net: torch.nn.Module, trainloader: DataLoader, epochs: int, lr: float, device: torch.device):
    """Train a YOLO model using Ultralytics."""

    if not isinstance(net, YoloWrapper):
        raise TypeError("Detection training expects a YoloWrapper model.")

    data_yaml = _write_resolved_yolo_yaml()
    yolo_data = _load_yolo_data_yaml(data_yaml)
    names = yolo_data.get("names")
    if names:
        net.yolo.model.names = names
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

    data_yaml = _write_resolved_yolo_yaml()
    yolo_data = _load_yolo_data_yaml(data_yaml)
    names = yolo_data.get("names")
    if names:
        net.yolo.model.names = names
    results = net.yolo.val(data=str(data_yaml), device=str(device))

    loss = 0.0
    map50 = 0.0
    if hasattr(results, "results_dict"):
        loss = float(results.results_dict.get("val/box_loss", 0.0))
        map50 = float(results.results_dict.get("metrics/mAP50", 0.0))
    return loss, map50
