from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BACKEND_ROOT / "data" / "veg_seg_3class" / "data.yaml"
DEFAULT_WEIGHTS = BACKEND_ROOT / "runs" / "segment_veg3" / "veg3_seg" / "weights" / "best.pt"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA)
    ap.add_argument("--split", type=str, default="val", choices=("val", "test"))
    ap.add_argument("--no-plots", action="store_true")
    args = ap.parse_args()

    data_yaml = args.data.resolve()
    weights = args.weights.resolve()
    if not data_yaml.is_file():
        print(f"Data yaml not found: {data_yaml}", file=sys.stderr)
        sys.exit(1)
    if not weights.is_file():
        print(f"Weights not found: {weights}", file=sys.stderr)
        sys.exit(1)

    from ultralytics import YOLO

    model = YOLO(str(weights))
    print(f"\n--- veg3_seg | split={args.split} ---\n")
    metrics = model.val(data=str(data_yaml), split=args.split, plots=not args.no_plots, verbose=False)

    box = metrics.box
    print(f"Box mAP@0.5: {float(box.map50):.4f}")
    print(f"Box P/R: {float(box.mp):.4f} / {float(box.mr):.4f}")
    seg = getattr(metrics, "seg", None)
    if seg is not None:
        print(f"Mask mAP@0.5: {float(getattr(seg, 'map50', 0.0) or 0.0):.4f}")
        if hasattr(seg, "mp"):
            print(f"Mask P/R: {float(seg.mp):.4f} / {float(seg.mr):.4f}")


if __name__ == "__main__":
    main()
