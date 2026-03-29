"""
Print per-class image counts and instance (box) counts for train-related folders.

Compares:
  - data/splits/train (original split)
  - data/augmented/train (augmented-only; skew vs split is expected)

Run from backend/:
    python scripts/report_class_balance.py
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dataset_common import BACKEND_ROOT, CONFIG_PATH, find_image_for_stem, load_classes_config


def scan_labels(labels_dir: Path, images_dir: Path, nc: int) -> tuple[dict[int, int], dict[int, int]]:
    """Returns (instances_per_class, images_with_class). Only labels paired with an image."""
    inst: dict[int, int] = defaultdict(int)
    img_hit: dict[int, set[str]] = defaultdict(set)

    if not labels_dir.is_dir():
        return {}, {}

    for lab in labels_dir.glob("*.txt"):
        stem = lab.stem
        if find_image_for_stem(images_dir, stem) is None:
            continue
        try:
            text = lab.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        seen: set[int] = set()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 5:
                continue
            try:
                cid = int(float(parts[0]))
            except ValueError:
                continue
            if cid < 0 or cid >= nc:
                continue
            inst[cid] += 1
            seen.add(cid)
        for c in seen:
            img_hit[c].add(stem)

    images_per_c = {i: len(img_hit[i]) for i in range(nc)}
    inst_per_c = {i: int(inst[i]) for i in range(nc)}
    return inst_per_c, images_per_c


def main() -> None:
    parser = argparse.ArgumentParser(description="Class balance report for train + augmented")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    args = parser.parse_args()

    cfg = load_classes_config(args.config)
    nc = cfg["nc"]
    order = cfg["canonical_order"]

    splits_i = BACKEND_ROOT / "data" / "splits" / "train" / "images"
    splits_l = BACKEND_ROOT / "data" / "splits" / "train" / "labels"
    aug_i = BACKEND_ROOT / "data" / "augmented" / "train" / "images"
    aug_l = BACKEND_ROOT / "data" / "augmented" / "train" / "labels"

    si, simg = scan_labels(splits_l, splits_i, nc)
    ai, aimg = scan_labels(aug_l, aug_i, nc)

    if not splits_l.is_dir():
        print("data/splits/train/labels not found; run split_dataset.py first", file=sys.stderr)

    print("=== images containing class (unique stems) ===")
    print(f"{'id':>3}  {'class':<14}  {'splits/train':>14}  {'augmented':>12}  {'sum':>10}  note")
    print("-" * 72)
    for i in range(nc):
        a, b = simg.get(i, 0), aimg.get(i, 0)
        s = a + b
        if s < 100:
            note = "low"
        elif s < 150:
            note = "ok"
        else:
            note = "ok+"
        print(f"{i:3d}  {order[i]:<14}  {a:14d}  {b:12d}  {s:10d}  {note}")

    print("\n=== instance counts (label lines / boxes) ===")
    print(f"{'id':>3}  {'class':<14}  {'splits/train':>14}  {'augmented':>12}  {'sum':>10}")
    print("-" * 60)
    for i in range(nc):
        a, b = si.get(i, 0), ai.get(i, 0)
        print(f"{i:3d}  {order[i]:<14}  {a:14d}  {b:12d}  {a+b:10d}")

    print(
        "\nNote: augmented/ holds only new crops; instance mix vs splits/train is expected to differ. "
        "Train with data/dataset.yaml (two train paths)."
    )


if __name__ == "__main__":
    main()
