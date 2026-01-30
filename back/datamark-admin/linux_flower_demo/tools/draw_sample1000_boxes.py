#!/usr/bin/env python3
"""Draw Pascal VOC boxes on images in sample-1000 dataset."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class Box:
    label: str
    xmin: float
    ymin: float
    xmax: float
    ymax: float


def _iter_images(root: Path) -> Iterable[Path]:
    exts = {".jpg", ".jpeg", ".png", ".bmp"}
    return (p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def _safe_float(text: str | None) -> float | None:
    if text is None:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _parse_voc(xml_path: Path) -> tuple[list[Box], tuple[float, float] | None]:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    size_node = root.find("size")
    xml_size = None
    if size_node is not None:
        w = _safe_float(size_node.findtext("width"))
        h = _safe_float(size_node.findtext("height"))
        if w and h:
            xml_size = (w, h)

    boxes: list[Box] = []
    for obj in root.findall("object"):
        label = obj.findtext("name") or "unknown"
        bnd = obj.find("bndbox")
        if bnd is None:
            continue
        xmin = _safe_float(bnd.findtext("xmin"))
        ymin = _safe_float(bnd.findtext("ymin"))
        xmax = _safe_float(bnd.findtext("xmax"))
        ymax = _safe_float(bnd.findtext("ymax"))
        if None in (xmin, ymin, xmax, ymax):
            continue
        boxes.append(Box(label=label, xmin=xmin, ymin=ymin, xmax=xmax, ymax=ymax))
    return boxes, xml_size


def _maybe_scale_boxes(
    boxes: list[Box], img_size: tuple[int, int], xml_size: tuple[float, float] | None
) -> list[Box]:
    if not boxes or not xml_size:
        return boxes

    img_w, img_h = img_size
    xml_w, xml_h = xml_size
    if xml_w <= 0 or xml_h <= 0:
        return boxes

    max_x = max(b.xmax for b in boxes)
    max_y = max(b.ymax for b in boxes)
    if max_x <= img_w and max_y <= img_h:
        return boxes

    # Only scale if boxes fit within xml_size but exceed image size.
    if max_x <= xml_w and max_y <= xml_h:
        scale_x = img_w / xml_w
        scale_y = img_h / xml_h
        return [
            Box(
                label=b.label,
                xmin=b.xmin * scale_x,
                ymin=b.ymin * scale_y,
                xmax=b.xmax * scale_x,
                ymax=b.ymax * scale_y,
            )
            for b in boxes
        ]

    return boxes


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(value, hi))


def _draw_boxes(image: Image.Image, boxes: list[Box], clamp: bool) -> Image.Image:
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    w, h = image.size

    for box in boxes:
        xmin, ymin, xmax, ymax = box.xmin, box.ymin, box.xmax, box.ymax
        if clamp:
            xmin = _clamp(xmin, 0, w - 1)
            xmax = _clamp(xmax, 0, w - 1)
            ymin = _clamp(ymin, 0, h - 1)
            ymax = _clamp(ymax, 0, h - 1)

        color = (255, 0, 0)
        draw.rectangle([xmin, ymin, xmax, ymax], outline=color, width=2)

        label = box.label
        if label:
            text_w, text_h = draw.textsize(label, font=font)
            text_x = xmin
            text_y = max(0, ymin - text_h - 2)
            draw.rectangle([text_x, text_y, text_x + text_w + 4, text_y + text_h + 2], fill=color)
            draw.text((text_x + 2, text_y + 1), label, fill=(255, 255, 255), font=font)

    return image


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draw Pascal VOC boxes on sample-1000 images and save copies."
    )
    parser.add_argument(
        "--input",
        default=str(
            Path(__file__).resolve().parents[1] / "allDatasets" / "sample-1000"
        ),
        help="Input dataset root (default: linux_flower_demo/allDatasets/sample-1000)",
    )
    parser.add_argument(
        "--output",
        default=str(
            Path(__file__).resolve().parents[1] / "allDatasets" / "sample-1000-boxed"
        ),
        help="Output root for boxed images",
    )
    parser.add_argument(
        "--no-clamp",
        action="store_true",
        help="Do not clamp boxes to image bounds",
    )
    args = parser.parse_args()

    input_root = Path(args.input).resolve()
    output_root = Path(args.output).resolve()
    clamp = not args.no_clamp

    if not input_root.exists():
        print(f"[error] input root not found: {input_root}")
        return 1

    images = list(_iter_images(input_root))
    if not images:
        print(f"[error] no images found under: {input_root}")
        return 1

    output_root.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0
    for image_path in images:
        xml_path = image_path.with_suffix(".xml")
        if not xml_path.exists():
            skipped += 1
            continue

        try:
            boxes, xml_size = _parse_voc(xml_path)
        except Exception as exc:
            print(f"[warn] failed to parse {xml_path}: {exc}")
            skipped += 1
            continue

        try:
            image = Image.open(image_path).convert("RGB")
        except Exception as exc:
            print(f"[warn] failed to open {image_path}: {exc}")
            skipped += 1
            continue

        boxes = _maybe_scale_boxes(boxes, image.size, xml_size)
        boxed = _draw_boxes(image, boxes, clamp=clamp)

        rel_path = image_path.relative_to(input_root)
        out_path = output_root / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        boxed.save(out_path)
        processed += 1

    print(f"input: {input_root}")
    print(f"output: {output_root}")
    print(f"processed images: {processed}")
    print(f"skipped (missing xml / errors): {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
