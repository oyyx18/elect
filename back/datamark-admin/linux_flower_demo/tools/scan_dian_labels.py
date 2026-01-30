#!/usr/bin/env python3
"""Scan YOLO labels for format issues and class id validity."""

from __future__ import annotations

import argparse
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


def _try_import_yaml():
    try:
        import yaml  # type: ignore

        return yaml
    except Exception:
        return None


def _parse_yaml_fallback(path: Path) -> dict:
    data: dict = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            data[key] = value
        else:
            data[key] = value
    return data


def _load_data_yaml(path: Path) -> dict:
    yaml_mod = _try_import_yaml()
    if yaml_mod is not None:
        return yaml_mod.safe_load(path.read_text(encoding="utf-8", errors="replace")) or {}
    return _parse_yaml_fallback(path)


def _resolve_root(data_yaml: Path, value: str | None) -> Path:
    if not value:
        return data_yaml.parent.resolve()

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate

    # Try a few bases (data.yaml parent, then higher parents) until one exists.
    for base in [data_yaml.parent, *data_yaml.parents]:
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved

    # Fallback to data.yaml parent if nothing exists.
    return (data_yaml.parent / candidate).resolve()


def _resolve_images_dir(root: Path, value: str) -> Path:
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _label_path_for_image(images_dir: Path, labels_dir: Path, image_path: Path) -> Path:
    rel = image_path.relative_to(images_dir)
    return labels_dir / rel.with_suffix(".txt")


def _iter_images(images_dir: Path) -> Iterable[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    if not images_dir.exists():
        return []
    return (p for p in images_dir.rglob("*") if p.suffix.lower() in exts)


def _safe_float(value: str) -> float | None:
    try:
        return float(value)
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan YOLO labels for dian dataset.")
    parser.add_argument(
        "--data-yaml",
        default=str(Path(__file__).resolve().parents[1] / "allDatasets" / "dian" / "data.yaml"),
        help="Path to data.yaml (default: linux_flower_demo/allDatasets/dian/data.yaml)",
    )
    args = parser.parse_args()

    data_yaml = Path(args.data_yaml).resolve()
    if not data_yaml.exists():
        print(f"[error] data.yaml not found: {data_yaml}")
        return 1

    data = _load_data_yaml(data_yaml)
    root = _resolve_root(data_yaml, data.get("path"))
    nc = data.get("nc")
    try:
        nc = int(nc) if nc is not None else None
    except Exception:
        nc = None

    splits = {}
    for key in ("train", "val", "valid", "test"):
        if key in data and data[key]:
            splits[key] = _resolve_images_dir(root, str(data[key]))
    if "val" not in splits and "valid" in splits:
        splits["val"] = splits["valid"]

    if not splits:
        print("[error] No train/val/test splits found in data.yaml.")
        return 1

    counts = Counter()
    column_hist = Counter()
    class_hist = Counter()
    bad_rows = []
    out_of_range = Counter()
    coord_stats = defaultdict(lambda: {"min": math.inf, "max": -math.inf})

    for split_name, images_dir in splits.items():
        labels_dir = images_dir.parent / "labels"
        images = list(_iter_images(images_dir))
        counts[f"{split_name}_images"] = len(images)

        for image_path in images:
            label_path = _label_path_for_image(images_dir, labels_dir, image_path)
            if not label_path.exists():
                counts[f"{split_name}_missing_labels"] += 1
                continue

            content = label_path.read_text(encoding="utf-8", errors="replace")
            lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
            if not lines:
                counts[f"{split_name}_empty_labels"] += 1
                continue

            for line_no, line in enumerate(lines, start=1):
                parts = line.split()
                column_hist[len(parts)] += 1

                if len(parts) < 5:
                    counts["invalid_rows"] += 1
                    bad_rows.append((label_path, line_no, line))
                    continue

                class_id = _safe_float(parts[0])
                if class_id is None or not float(class_id).is_integer():
                    counts["invalid_class_id"] += 1
                else:
                    class_id = int(class_id)
                    class_hist[class_id] += 1
                    if nc is not None and not (0 <= class_id < nc):
                        out_of_range[class_id] += 1

                # track coordinate ranges for the first 4 numbers after class id
                coords = parts[1:5]
                for idx, value in enumerate(coords):
                    fval = _safe_float(value)
                    if fval is None:
                        counts["invalid_coords"] += 1
                        break
                    coord_stats[idx]["min"] = min(coord_stats[idx]["min"], fval)
                    coord_stats[idx]["max"] = max(coord_stats[idx]["max"], fval)

                # segmentation-style rows often have > 5 columns
                if len(parts) > 5:
                    counts["segmentation_rows"] += 1

    print(f"data.yaml: {data_yaml}")
    print(f"root: {root}")
    print(f"nc: {nc}")
    print("")
    print("Split summary:")
    for split_name in sorted(splits.keys()):
        total = counts.get(f"{split_name}_images", 0)
        missing = counts.get(f"{split_name}_missing_labels", 0)
        empty = counts.get(f"{split_name}_empty_labels", 0)
        missing_rate = (missing / total * 100.0) if total else 0.0
        empty_rate = (empty / total * 100.0) if total else 0.0
        print(
            f"- {split_name}: images={total}, missing_labels={missing} ({missing_rate:.2f}%), "
            f"empty_labels={empty} ({empty_rate:.2f}%)"
        )

    print("")
    print("Label row stats:")
    print(f"- invalid_rows: {counts.get('invalid_rows', 0)}")
    print(f"- invalid_class_id: {counts.get('invalid_class_id', 0)}")
    print(f"- invalid_coords: {counts.get('invalid_coords', 0)}")
    print(f"- segmentation_rows(>5 cols): {counts.get('segmentation_rows', 0)}")

    print("")
    print("Column count histogram:")
    for cols, cnt in sorted(column_hist.items()):
        print(f"- cols={cols}: {cnt}")

    if nc is not None:
        print("")
        print("Class id counts (including out-of-range):")
        for cls_id, cnt in sorted(class_hist.items()):
            out = out_of_range.get(cls_id, 0)
            flag = " [out-of-range]" if out else ""
            print(f"- class {cls_id}: {cnt}{flag}")
        if out_of_range:
            print("Out-of-range class ids:")
            for cls_id, cnt in sorted(out_of_range.items()):
                print(f"- class {cls_id}: {cnt}")

    print("")
    print("Coord ranges (expect ~0..1 if normalized):")
    for idx, name in enumerate(["x_center", "y_center", "width", "height"]):
        stats = coord_stats[idx]
        if stats["min"] is math.inf:
            print(f"- {name}: (no data)")
        else:
            print(f"- {name}: min={stats['min']:.6f}, max={stats['max']:.6f}")

    if bad_rows:
        print("")
        print("Sample invalid rows (up to 10):")
        for entry in bad_rows[:10]:
            print(f"- {entry[0]}:{entry[1]} -> {entry[2]}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
