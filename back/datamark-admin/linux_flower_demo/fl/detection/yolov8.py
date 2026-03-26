"""Flower detection task backed by YOLOv8n."""

from __future__ import annotations

import copy
import os
import random
import shutil
from ast import literal_eval
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any
from xml.etree import ElementTree as ET

import torch
import torch.nn as nn

try:
    import yaml
except Exception:  # pragma: no cover - optional dependency path
    yaml = None

try:
    from ultralytics import YOLO
except Exception as exc:  # pragma: no cover - depends on local environment
    YOLO = None
    _YOLO_IMPORT_ERROR: Exception | None = exc
else:
    _YOLO_IMPORT_ERROR = None


IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".bmp")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = Path(
    os.getenv(
        "FLOWER_DETECTION_DATASET",
        PROJECT_ROOT / "allDatasets" / "sample-1000-new",
    )
).resolve()
CACHE_ROOT = Path(
    os.getenv(
        "FLOWER_DETECTION_CACHE",
        PROJECT_ROOT / ".flower_detection_cache",
    )
).resolve()
RUNS_ROOT = Path(
    os.getenv(
        "FLOWER_YOLO_RUNS",
        PROJECT_ROOT / ".flower_yolo_runs",
    )
).resolve()
DATASET_FORMAT = os.getenv("FLOWER_DETECTION_DATASET_FORMAT", "").strip().upper()

DEFAULT_BATCH_SIZE = int(os.getenv("FLOWER_BATCH_SIZE", "8"))
VAL_RATIO = float(os.getenv("FLOWER_DETECTION_VAL_RATIO", "0.2"))
DATA_SEED = int(os.getenv("FLOWER_DETECTION_SEED", "42"))
YOLO_IMAGE_SIZE = int(os.getenv("FLOWER_YOLO_IMGSZ", "640"))
YOLO_WORKERS = int(os.getenv("FLOWER_YOLO_WORKERS", "0"))
METRIC_NAME = "map50"
MAX_SKIPPED_EXAMPLES_TO_LOG = 5

_PREPARE_LOCK = Lock()
_PREPARED_DATASET: "PreparedDataset | None" = None


@dataclass(frozen=True)
class VocBox:
    label: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float


@dataclass(frozen=True)
class RawSample:
    image_path: Path
    xml_path: Path
    width: int
    height: int
    boxes: tuple[VocBox, ...]


@dataclass(frozen=True)
class ConvertedSample:
    image_path: Path
    label_path: Path


@dataclass(frozen=True)
class PreparedDataset:
    class_names: tuple[str, ...]
    train_samples: tuple[ConvertedSample, ...]
    val_samples: tuple[ConvertedSample, ...]


@dataclass
class DetectionDatasetView:
    samples: list[ConvertedSample]
    yaml_path: Path
    batch_size: int
    split: str
    partition_id: int
    dataset: list[ConvertedSample] = field(init=False)

    def __post_init__(self) -> None:
        self.dataset = self.samples


def _require_ultralytics() -> None:
    if YOLO is None:
        raise ImportError(
            "The detection task requires 'ultralytics'. "
            "Install project dependencies before running Flower detection."
        ) from _YOLO_IMPORT_ERROR


def _resolve_model_source() -> str:
    env_value = os.getenv("FLOWER_YOLO_MODEL")
    if env_value:
        return env_value

    for candidate in (
        PROJECT_ROOT / "weights" / "yolov8n.pt",
        PROJECT_ROOT / "yolov8n.pt",
        Path.cwd() / "yolov8n.pt",
    ):
        if candidate.exists():
            return str(candidate)

    # Fall back to architecture-only config to avoid implicit downloads.
    return "yolov8n.yaml"


def _cpu_state_dict(state_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu() for name, tensor in state_dict.items()}


def _quoted_yaml(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def _safe_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _find_image_for_xml(xml_path: Path) -> Path | None:
    for suffix in IMAGE_SUFFIXES:
        candidate = xml_path.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def _parse_voc(xml_path: Path) -> tuple[int, int, tuple[VocBox, ...]]:
    root = ET.parse(xml_path).getroot()
    size_node = root.find("size")
    if size_node is None:
        raise ValueError(f"Missing <size> node: {xml_path}")

    width = _safe_float(size_node.findtext("width"))
    height = _safe_float(size_node.findtext("height"))
    if not width or not height:
        raise ValueError(f"Invalid image size in: {xml_path}")

    boxes: list[VocBox] = []
    for obj in root.findall("object"):
        label = (obj.findtext("name") or "").strip()
        bndbox = obj.find("bndbox")
        if not label or bndbox is None:
            continue

        xmin = _safe_float(bndbox.findtext("xmin"))
        ymin = _safe_float(bndbox.findtext("ymin"))
        xmax = _safe_float(bndbox.findtext("xmax"))
        ymax = _safe_float(bndbox.findtext("ymax"))
        if None in (xmin, ymin, xmax, ymax):
            continue

        boxes.append(VocBox(label=label, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))

    if not boxes:
        raise ValueError(f"No valid objects found in: {xml_path}")

    return int(width), int(height), tuple(boxes)


def _resolve_dataset_format() -> str:
    if DATASET_FORMAT in {"VOC", "YOLO"}:
        return DATASET_FORMAT
    if (DATASET_ROOT / "data.yaml").is_file():
        return "YOLO"
    if (DATASET_ROOT / "train" / "labels").is_dir():
        return "YOLO"
    if (DATASET_ROOT / "valid" / "labels").is_dir():
        return "YOLO"
    if (DATASET_ROOT / "val" / "labels").is_dir():
        return "YOLO"
    return "VOC"


def _parse_yaml_scalar(value: str) -> Any:
    text = value.strip()
    if not text:
        return ""
    lower_text = text.lower()
    if lower_text == "true":
        return True
    if lower_text == "false":
        return False
    try:
        return literal_eval(text)
    except (ValueError, SyntaxError):
        return text.strip("'\"")


def _load_dataset_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    raw_text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(raw_text)
        if isinstance(loaded, dict):
            return loaded

    payload: dict[str, Any] = {}
    current_key: str | None = None
    current_mapping: dict[Any, Any] = {}
    for raw_line in raw_text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        if line[:1].isspace():
            if current_key is None:
                continue
            stripped = line.strip()
            if ":" not in stripped:
                continue
            child_key, child_value = stripped.split(":", 1)
            current_mapping[_parse_yaml_scalar(child_key)] = _parse_yaml_scalar(child_value)
            continue

        if current_key is not None:
            payload[current_key] = current_mapping
            current_key = None
            current_mapping = {}

        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            payload[key] = _parse_yaml_scalar(value)
        else:
            current_key = key
            current_mapping = {}

    if current_key is not None:
        payload[current_key] = current_mapping

    return payload


def _normalize_class_names(names_value: Any) -> tuple[str, ...]:
    if isinstance(names_value, dict):
        items: list[tuple[int, str]] = []
        for key, value in names_value.items():
            try:
                index = int(key)
            except (TypeError, ValueError):
                continue
            items.append((index, str(value)))
        if items:
            return tuple(name for _, name in sorted(items, key=lambda item: item[0]))

    if isinstance(names_value, (list, tuple)):
        return tuple(str(value) for value in names_value)

    if isinstance(names_value, str):
        parsed = _parse_yaml_scalar(names_value)
        if parsed != names_value:
            return _normalize_class_names(parsed)

    return ()


def _resolve_dataset_base_dir(dataset_yaml: Path, payload: dict[str, Any]) -> Path:
    configured_path = payload.get("path")
    if not configured_path:
        return DATASET_ROOT

    candidate = Path(str(configured_path))
    if candidate.is_absolute():
        return candidate.resolve()
    return (dataset_yaml.parent / candidate).resolve()


def _resolve_split_source(base_dir: Path, split_value: Any) -> Path | None:
    if not split_value:
        return None
    candidate = Path(str(split_value))
    if candidate.is_absolute():
        return candidate.resolve()
    return (base_dir / candidate).resolve()


def _iter_image_paths_from_source(source: Path | None) -> list[Path]:
    if source is None or not source.exists():
        return []

    if source.is_file():
        image_paths: list[Path] = []
        for raw_line in source.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            candidate = Path(line)
            if not candidate.is_absolute():
                candidate = (source.parent / candidate).resolve()
            else:
                candidate = candidate.resolve()
            if candidate.suffix.lower() in IMAGE_SUFFIXES and candidate.exists():
                image_paths.append(candidate)
        return sorted(image_paths)

    return sorted(
        path.resolve()
        for path in source.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def _resolve_yolo_label_path(image_path: Path) -> Path | None:
    parts = list(image_path.parts)
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] != "images":
            continue
        candidate = Path(*parts[:index], "labels", *parts[index + 1 :]).with_suffix(".txt")
        if candidate.exists():
            return candidate.resolve()

    candidate = image_path.with_suffix(".txt")
    if candidate.exists():
        return candidate.resolve()
    return None


def _read_yolo_class_ids(label_path: Path) -> set[int]:
    class_ids: set[int] = set()
    for raw_line in label_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        parts = stripped.split()
        if not parts:
            continue
        try:
            class_ids.add(int(float(parts[0])))
        except (TypeError, ValueError):
            continue
    return class_ids


def _collect_yolo_samples(split_name: str, source: Path | None) -> list[ConvertedSample]:
    image_paths = _iter_image_paths_from_source(source)
    if not image_paths:
        return []

    samples: list[ConvertedSample] = []
    missing_labels = 0
    empty_labels = 0
    for image_path in image_paths:
        label_path = _resolve_yolo_label_path(image_path)
        if label_path is None:
            missing_labels += 1
            continue
        if not _read_yolo_class_ids(label_path):
            empty_labels += 1
            continue
        samples.append(
            ConvertedSample(
                image_path=image_path,
                label_path=label_path,
            )
        )

    print(
        f"Loaded YOLO split '{split_name}': kept {len(samples)}/{len(image_paths)} images, "
        f"skipped {missing_labels} missing labels, skipped {empty_labels} empty labels."
    )
    return samples


def _build_yolo_class_names(
    payload: dict[str, Any],
    samples: list[ConvertedSample],
) -> tuple[str, ...]:
    class_names = _normalize_class_names(payload.get("names"))
    if class_names:
        return class_names

    num_classes = payload.get("nc")
    if isinstance(num_classes, int) and num_classes > 0:
        return tuple(str(index) for index in range(num_classes))
    if isinstance(num_classes, str):
        try:
            parsed_num_classes = int(num_classes)
        except ValueError:
            parsed_num_classes = 0
        if parsed_num_classes > 0:
            return tuple(str(index) for index in range(parsed_num_classes))

    max_class_id = -1
    for sample in samples:
        class_ids = _read_yolo_class_ids(sample.label_path)
        if class_ids:
            max_class_id = max(max_class_id, max(class_ids))
    if max_class_id >= 0:
        return tuple(str(index) for index in range(max_class_id + 1))

    raise ValueError(f"Unable to determine class names for YOLO dataset: {DATASET_ROOT}")


def _prepare_yolo_dataset() -> PreparedDataset:
    dataset_yaml = DATASET_ROOT / "data.yaml"
    payload = _load_dataset_yaml(dataset_yaml) if dataset_yaml.exists() else {}
    base_dir = _resolve_dataset_base_dir(dataset_yaml, payload) if dataset_yaml.exists() else DATASET_ROOT

    train_source = _resolve_split_source(base_dir, payload.get("train"))
    if train_source is None:
        train_source = _resolve_split_source(base_dir, "train/images")

    val_source = _resolve_split_source(base_dir, payload.get("val") or payload.get("valid"))
    if val_source is None:
        for candidate in ("valid/images", "val/images", "test/images"):
            candidate_path = _resolve_split_source(base_dir, candidate)
            if candidate_path is not None and candidate_path.exists():
                val_source = candidate_path
                break

    train_samples = _collect_yolo_samples("train", train_source)
    val_samples = _collect_yolo_samples("val", val_source)
    all_samples = train_samples + val_samples

    if not all_samples:
        raise FileNotFoundError(f"No YOLO samples found under: {DATASET_ROOT}")

    class_names = _build_yolo_class_names(payload, all_samples)

    if not train_samples:
        train_samples = list(val_samples)
    if not val_samples:
        train_tuple, val_tuple = _split_samples(list(train_samples))
        train_samples = list(train_tuple)
        val_samples = list(val_tuple)

    return PreparedDataset(
        class_names=class_names,
        train_samples=tuple(train_samples),
        val_samples=tuple(val_samples),
    )


def _discover_voc_samples() -> list[RawSample]:
    if not DATASET_ROOT.exists():
        raise FileNotFoundError(f"Detection dataset not found: {DATASET_ROOT}")

    samples: list[RawSample] = []
    missing_images: list[Path] = []
    for xml_path in sorted(DATASET_ROOT.rglob("*.xml")):
        image_path = _find_image_for_xml(xml_path)
        if image_path is None:
            missing_images.append(xml_path)
            continue

        width, height, boxes = _parse_voc(xml_path)
        samples.append(
            RawSample(
                image_path=image_path,
                xml_path=xml_path,
                width=width,
                height=height,
                boxes=boxes,
            )
        )

    if missing_images:
        raise FileNotFoundError(
            f"Found XML files without sibling images, for example: {missing_images[0]}"
        )
    if not samples:
        raise FileNotFoundError(f"No Pascal VOC samples found under: {DATASET_ROOT}")

    return samples


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(value, upper))


def _voc_to_yolo_lines(
    boxes: tuple[VocBox, ...],
    width: int,
    height: int,
    class_to_id: dict[str, int],
) -> tuple[str | None, int]:
    lines: list[str] = []
    dropped_boxes = 0
    for box in boxes:
        xmin = _clamp(box.xmin, 0.0, float(width))
        xmax = _clamp(box.xmax, 0.0, float(width))
        ymin = _clamp(box.ymin, 0.0, float(height))
        ymax = _clamp(box.ymax, 0.0, float(height))
        if xmax <= xmin or ymax <= ymin:
            dropped_boxes += 1
            continue

        center_x = ((xmin + xmax) / 2.0) / width
        center_y = ((ymin + ymax) / 2.0) / height
        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height
        lines.append(
            f"{class_to_id[box.label]} "
            f"{center_x:.6f} {center_y:.6f} {box_width:.6f} {box_height:.6f}"
        )

    if not lines:
        return None, dropped_boxes
    return "\n".join(lines) + "\n", dropped_boxes


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _copy_file_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    shutil.copy2(source, tmp_path)
    tmp_path.replace(target)


def _normalized_paths(image_path: Path) -> tuple[Path, Path]:
    relative_path = image_path.relative_to(DATASET_ROOT)
    normalized_image = CACHE_ROOT / "normalized" / "images" / "all" / relative_path
    normalized_label = (CACHE_ROOT / "normalized" / "labels" / "all" / relative_path).with_suffix(
        ".txt"
    )
    return normalized_image, normalized_label


def _split_samples(
    samples: list[ConvertedSample],
) -> tuple[tuple[ConvertedSample, ...], tuple[ConvertedSample, ...]]:
    shuffled = list(samples)
    random.Random(DATA_SEED).shuffle(shuffled)

    if len(shuffled) == 1:
        return (tuple(shuffled), tuple(shuffled))

    val_count = max(1, int(len(shuffled) * VAL_RATIO))
    val_count = min(val_count, len(shuffled) - 1)
    val_samples = tuple(shuffled[:val_count])
    train_samples = tuple(shuffled[val_count:])
    return train_samples, val_samples


def _prepare_dataset() -> PreparedDataset:
    global _PREPARED_DATASET

    if _PREPARED_DATASET is not None:
        return _PREPARED_DATASET

    with _PREPARE_LOCK:
        if _PREPARED_DATASET is not None:
            return _PREPARED_DATASET

        dataset_format = _resolve_dataset_format()
        if dataset_format == "YOLO":
            _PREPARED_DATASET = _prepare_yolo_dataset()
            return _PREPARED_DATASET
        if dataset_format != "VOC":
            raise ValueError(f"Unsupported detection dataset format: {dataset_format}")

        raw_samples = _discover_voc_samples()
        class_names = tuple(sorted({box.label for sample in raw_samples for box in sample.boxes}))
        class_to_id = {name: idx for idx, name in enumerate(class_names)}

        converted_samples: list[ConvertedSample] = []
        skipped_samples: list[Path] = []
        dropped_boxes = 0
        for sample in raw_samples:
            normalized_image, normalized_label = _normalized_paths(sample.image_path)

            label_text, sample_dropped_boxes = _voc_to_yolo_lines(
                sample.boxes,
                sample.width,
                sample.height,
                class_to_id,
            )
            dropped_boxes += sample_dropped_boxes
            if label_text is None:
                skipped_samples.append(sample.xml_path)
                continue

            normalized_image.parent.mkdir(parents=True, exist_ok=True)
            normalized_label.parent.mkdir(parents=True, exist_ok=True)

            if not normalized_image.exists():
                _copy_file_atomic(sample.image_path, normalized_image)

            _write_text_atomic(normalized_label, label_text)
            converted_samples.append(
                ConvertedSample(
                    image_path=normalized_image,
                    label_path=normalized_label,
                )
            )

        if not converted_samples:
            raise ValueError("No valid annotations remain after VOC to YOLO conversion")

        print(
            "Prepared detection dataset: "
            f"kept {len(converted_samples)}/{len(raw_samples)} images, "
            f"skipped {len(skipped_samples)} empty annotations, "
            f"dropped {dropped_boxes} invalid boxes."
        )
        if skipped_samples:
            preview = ", ".join(str(path) for path in skipped_samples[:MAX_SKIPPED_EXAMPLES_TO_LOG])
            print(f"Skipped invalid annotation files (first {min(len(skipped_samples), MAX_SKIPPED_EXAMPLES_TO_LOG)}): {preview}")

        train_samples, val_samples = _split_samples(converted_samples)
        _PREPARED_DATASET = PreparedDataset(
            class_names=class_names,
            train_samples=train_samples,
            val_samples=val_samples,
        )
        return _PREPARED_DATASET


def _partition_samples(
    samples: tuple[ConvertedSample, ...],
    partition_id: int,
    num_partitions: int,
) -> list[ConvertedSample]:
    return [sample for idx, sample in enumerate(samples) if idx % num_partitions == partition_id]


def _ensure_nonempty(
    train_samples: list[ConvertedSample],
    val_samples: list[ConvertedSample],
) -> tuple[list[ConvertedSample], list[ConvertedSample]]:
    if not train_samples and not val_samples:
        raise ValueError("No samples available for this partition")
    if not train_samples:
        train_samples = list(val_samples)
    if not val_samples:
        val_samples = train_samples[:1]
    return train_samples, val_samples


def _write_dataset_yaml(
    output_dir: Path,
    train_samples: list[ConvertedSample],
    val_samples: list[ConvertedSample],
    class_names: tuple[str, ...],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)

    train_txt = output_dir / "train.txt"
    val_txt = output_dir / "val.txt"
    yaml_path = output_dir / "dataset.yaml"

    _write_text_atomic(train_txt, "\n".join(str(sample.image_path) for sample in train_samples) + "\n")
    _write_text_atomic(val_txt, "\n".join(str(sample.image_path) for sample in val_samples) + "\n")

    names_lines = "\n".join(
        f"  {index}: {_quoted_yaml(name)}" for index, name in enumerate(class_names)
    )
    yaml_content = (
        f"train: {_quoted_yaml(str(train_txt))}\n"
        f"val: {_quoted_yaml(str(val_txt))}\n"
        "names:\n"
        f"{names_lines}\n"
    )
    _write_text_atomic(yaml_path, yaml_content)
    return yaml_path


def _to_yolo_device(device: torch.device) -> str | int:
    if device.type == "cuda":
        return 0 if device.index is None else device.index
    return "cpu"


def _build_yolo_from_net(net: nn.Module):
    _require_ultralytics()
    prepared = _prepare_dataset()
    yolo = YOLO(_resolve_model_source())
    yolo.model = copy.deepcopy(net).cpu()
    yolo.model.names = {idx: name for idx, name in enumerate(prepared.class_names)}
    return yolo


def _sync_net_from_yolo(net: nn.Module, yolo: Any) -> None:
    net.load_state_dict(_cpu_state_dict(yolo.model.state_dict()), strict=True)


def _extract_metrics(result: Any) -> dict[str, float]:
    metrics: dict[str, float] = {}

    result_dict = getattr(result, "results_dict", None)
    if isinstance(result_dict, dict):
        for key, value in result_dict.items():
            try:
                metrics[str(key).replace("(B)", "").replace("metrics/", "")] = float(value)
            except (TypeError, ValueError):
                continue

    box_metrics = getattr(result, "box", None)
    if box_metrics is not None:
        for source_name, target_name in (
            ("map50", "map50"),
            ("map", "map"),
            ("mp", "precision"),
            ("mr", "recall"),
        ):
            value = getattr(box_metrics, source_name, None)
            if value is not None:
                metrics[target_name] = float(value)

    return metrics


def _extract_loss(metrics: dict[str, float]) -> float:
    for key in ("loss", "val/loss", "train/loss", "box_loss", "cls_loss", "dfl_loss"):
        if key in metrics:
            return float(metrics[key])

    primary_metric = float(metrics.get(METRIC_NAME, 0.0))
    return max(0.0, 1.0 - primary_metric)


def Net() -> nn.Module:
    """Create the YOLOv8n detector used by Flower."""

    _require_ultralytics()
    prepared = _prepare_dataset()
    num_classes = len(prepared.class_names)

    from ultralytics.nn.tasks import DetectionModel

    model_source = _resolve_model_source()
    if model_source.endswith(".pt"):
        pretrained = YOLO(model_source).model
        model_cfg = getattr(pretrained, "yaml", None) or "yolov8n.yaml"
        model = DetectionModel(cfg=model_cfg, nc=num_classes, verbose=False)
        model_state = model.state_dict()
        compatible_state = {
            name: tensor
            for name, tensor in _cpu_state_dict(pretrained.state_dict()).items()
            if name in model_state and model_state[name].shape == tensor.shape
        }
        model.load_state_dict(compatible_state, strict=False)
        model.names = {idx: name for idx, name in enumerate(prepared.class_names)}
        return model

    model = DetectionModel(cfg=model_source, nc=num_classes, verbose=False)
    model.names = {idx: name for idx, name in enumerate(prepared.class_names)}
    return model


def load_data(partition_id: int, num_partitions: int, batch_size: int):
    """Load the partitioned detection dataset for one Flower client."""

    prepared = _prepare_dataset()
    train_samples = _partition_samples(prepared.train_samples, partition_id, num_partitions)
    val_samples = _partition_samples(prepared.val_samples, partition_id, num_partitions)
    train_samples, val_samples = _ensure_nonempty(train_samples, val_samples)

    partition_dir = CACHE_ROOT / "partitions" / f"{num_partitions}" / f"{partition_id}"
    yaml_path = _write_dataset_yaml(partition_dir, train_samples, val_samples, prepared.class_names)
    effective_batch_size = max(1, int(batch_size))

    train_view = DetectionDatasetView(
        samples=train_samples,
        yaml_path=yaml_path,
        batch_size=effective_batch_size,
        split="train",
        partition_id=partition_id,
    )
    val_view = DetectionDatasetView(
        samples=val_samples,
        yaml_path=yaml_path,
        batch_size=effective_batch_size,
        split="val",
        partition_id=partition_id,
    )
    return train_view, val_view


def load_centralized_dataset() -> DetectionDatasetView:
    """Load the global validation dataset for server-side evaluation."""

    prepared = _prepare_dataset()
    output_dir = CACHE_ROOT / "centralized"
    yaml_path = _write_dataset_yaml(
        output_dir,
        list(prepared.train_samples),
        list(prepared.val_samples),
        prepared.class_names,
    )
    return DetectionDatasetView(
        samples=list(prepared.val_samples),
        yaml_path=yaml_path,
        batch_size=DEFAULT_BATCH_SIZE,
        split="val",
        partition_id=-1,
    )


def train(
    net: nn.Module,
    trainloader: DetectionDatasetView,
    epochs: int,
    lr: float,
    device: torch.device,
):
    """Train YOLOv8n on one Flower client and sync weights back into `net`."""

    yolo = _build_yolo_from_net(net)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)

    result = yolo.train(
        data=str(trainloader.yaml_path),
        epochs=max(1, int(epochs)),
        batch=trainloader.batch_size,
        imgsz=YOLO_IMAGE_SIZE,
        lr0=float(lr),
        device=_to_yolo_device(device),
        workers=YOLO_WORKERS,
        project=str(RUNS_ROOT),
        name=f"client-{trainloader.partition_id}",
        exist_ok=True,
        verbose=False,
        plots=False,
        save=True,
    )

    _sync_net_from_yolo(net, yolo)
    metrics = _extract_metrics(result)
    return _extract_loss(metrics), metrics


def test(
    net: nn.Module,
    testloader: DetectionDatasetView,
    device: torch.device,
):
    """Evaluate YOLOv8n using the given dataset view."""

    yolo = _build_yolo_from_net(net)
    RUNS_ROOT.mkdir(parents=True, exist_ok=True)

    result = yolo.val(
        data=str(testloader.yaml_path),
        batch=testloader.batch_size,
        imgsz=YOLO_IMAGE_SIZE,
        device=_to_yolo_device(device),
        workers=YOLO_WORKERS,
        project=str(RUNS_ROOT),
        name=f"eval-{testloader.partition_id}",
        exist_ok=True,
        verbose=False,
        plots=False,
        save_json=False,
    )

    metrics = _extract_metrics(result)
    return _extract_loss(metrics), metrics


def save_model(state_dict: dict[str, torch.Tensor], output_path: Path) -> None:
    """Persist the federated model weights and minimal metadata."""

    prepared = _prepare_dataset()
    payload = {
        "state_dict": _cpu_state_dict(state_dict),
        "class_names": list(prepared.class_names),
        "model_source": _resolve_model_source(),
    }
    torch.save(payload, output_path)


__all__ = [
    "METRIC_NAME",
    "Net",
    "load_data",
    "load_centralized_dataset",
    "save_model",
    "test",
    "train",
]
