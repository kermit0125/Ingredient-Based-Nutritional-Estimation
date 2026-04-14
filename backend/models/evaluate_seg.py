"""Ultralytics validation for YOLOv8-seg: box + mask metrics on val/test."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BACKEND_ROOT / "data" / "splits_seg" / "data.yaml"
DEFAULT_WEIGHTS = BACKEND_ROOT / "runs" / "segment" / "veg_seg_v5" / "weights" / "best.pt"
TARGET_MAP50 = 0.60


def main() -> None:
    ap = argparse.ArgumentParser(description="Validate a YOLOv8-seg checkpoint (mAP box + mask).")
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--split", type=str, default="val", choices=("val", "test"))
    ap.add_argument("--no-plots", action="store_true", help="Disable Ultralytics PR/confusion plots.")
    args = ap.parse_args()

    data_yaml = args.data.resolve()
    weights = args.weights.resolve()
    if not data_yaml.is_file():
        print(f"Data yaml not found: {data_yaml}", file=sys.stderr)
        print("Run: python scripts/convert_detect_labels_to_seg.py", file=sys.stderr)
        sys.exit(1)
    if not weights.is_file():
        print(f"Weights not found: {weights}", file=sys.stderr)
        sys.exit(1)

    plots = not args.no_plots

    from ultralytics import YOLO

    model = YOLO(str(weights))
    print(f"\n--- YOLOv8-seg val | split={args.split} | data={data_yaml.name} ---\n")
    metrics = model.val(data=str(data_yaml), split=args.split, plots=plots, verbose=False)

    box = metrics.box
    map50 = float(box.map50)
    print(f"Box mAP@0.5: {map50:.4f}  (target reference >= {TARGET_MAP50} for detection stage)")
    print(f"Box Precision (mean): {float(box.mp):.4f}")
    print(f"Box Recall (mean): {float(box.mr):.4f}")

    seg = getattr(metrics, "seg", None)
    if seg is not None:
        smap50 = float(getattr(seg, "map50", 0.0) or 0.0)
        print(f"Mask mAP@0.5: {smap50:.4f}")
        if hasattr(seg, "mp"):
            print(f"Mask Precision (mean): {float(seg.mp):.4f}")
        if hasattr(seg, "mr"):
            print(f"Mask Recall (mean): {float(seg.mr):.4f}")
    else:
        print("Mask metrics not present on metrics object (unexpected for a .pt trained with segment).")

    print(f"\nPlots and CSV (if enabled) under the run directory associated with this val call.")


if __name__ == "__main__":
    main()
