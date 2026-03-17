#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def fix_xml_size(
    src_path: Path, dst_path: Path, width: int, height: int, depth: int | None
) -> bool:
    try:
        tree = ET.parse(src_path)
    except ET.ParseError as exc:
        print(f"[WARN] XML parse failed: {src_path} ({exc})")
        return False

    root = tree.getroot()
    size = root.find("size")
    if size is None:
        print(f"[WARN] <size> not found: {src_path}")
        return False

    width_el = size.find("width")
    height_el = size.find("height")
    depth_el = size.find("depth")

    if width_el is None or height_el is None:
        print(f"[WARN] <width>/<height> not found: {src_path}")
        return False

    width_el.text = str(width)
    height_el.text = str(height)
    if depth_el is not None and depth is not None:
        depth_el.text = str(depth)

    ET.indent(tree, space="  ", level=0)
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(dst_path, encoding="utf-8", xml_declaration=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Copy dataset and fix <size> in Pascal VOC XML labels."
    )
    parser.add_argument(
        "--src",
        default="linux_flower_demo/allDatasets/sample-1000",
        help="Source dataset directory",
    )
    parser.add_argument(
        "--dst",
        default="linux_flower_demo/allDatasets/sample-1000-new",
        help="Destination dataset directory",
    )
    parser.add_argument("--width", type=int, default=1920, help="Target width")
    parser.add_argument("--height", type=int, default=1080, help="Target height")
    parser.add_argument("--depth", type=int, default=3, help="Target depth")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow overwriting an existing destination directory",
    )
    args = parser.parse_args()

    src_dir = Path(args.src)
    dst_dir = Path(args.dst)

    if not src_dir.exists() or not src_dir.is_dir():
        print(f"[ERROR] Source not found: {src_dir}")
        return 2

    if dst_dir.exists():
        if not args.overwrite:
            print(f"[ERROR] Destination already exists: {dst_dir}")
            print("        Use --overwrite to replace files in the destination.")
            return 3
    else:
        dst_dir.mkdir(parents=True, exist_ok=True)

    xml_total = 0
    xml_ok = 0
    copied = 0

    for path in src_dir.rglob("*"):
        rel = path.relative_to(src_dir)
        target = dst_dir / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        if path.suffix.lower() == ".xml":
            xml_total += 1
            if fix_xml_size(path, target, args.width, args.height, args.depth):
                xml_ok += 1
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            copied += 1

    print(
        f"Done. XML fixed: {xml_ok}/{xml_total}. Non-XML files copied: {copied}. "
        f"Output: {dst_dir}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
