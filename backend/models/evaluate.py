"""
训练完成后评估：验证集整体指标、逐类 AP、test 集每类随机可视化；校验 nutrition_table.csv 覆盖全部类别。

从 backend/ 运行:
    python models/evaluate.py
    python models/evaluate.py --weights runs/detect/exp1/weights/best.pt
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from pathlib import Path

import cv2
import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA = BACKEND_ROOT / "data" / "splits" / "data.yaml"
DEFAULT_WEIGHTS = BACKEND_ROOT / "runs" / "detect" / "exp1" / "weights" / "best.pt"
NUTRITION_CSV = BACKEND_ROOT / "data" / "nutrition_table.csv"
TARGET_MAP50 = 0.60
WARN_AP50 = 0.50
SAMPLES_PER_CLASS = 3


def _load_names_from_data_yaml(data_yaml: Path) -> list[str]:
    d = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    names = d.get("names")
    if isinstance(names, dict):
        return [names[i] for i in sorted(int(k) for k in names)]
    if isinstance(names, list):
        return [str(x) for x in names]
    raise ValueError("data yaml missing names")


def _collect_test_images_by_class(
    data_yaml: Path,
) -> dict[int, list[Path]]:
    """Parse YOLO data yaml and scan test labels for class ids -> image paths."""
    from ultralytics.data.utils import check_det_dataset

    data = check_det_dataset(str(data_yaml))
    test_src = data.get("test")
    if not test_src:
        return {}
    test_paths = test_src if isinstance(test_src, list) else [test_src]
    images_roots = [Path(p) for p in test_paths]

    stem_to_path: dict[str, Path] = {}
    for root in images_roots:
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
                stem_to_path[p.stem] = p

    by_class: dict[int, set[str]] = {}
    for root in images_roots:
        labels_dir = root.parent / "labels"
        if not labels_dir.is_dir():
            continue
        for lp in labels_dir.glob("*.txt"):
            stem = lp.stem
            if stem not in stem_to_path:
                continue
            text = lp.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                parts = line.strip().split()
                if len(parts) < 5:
                    continue
                try:
                    cid = int(float(parts[0]))
                except ValueError:
                    continue
                by_class.setdefault(cid, set()).add(stem)

    out: dict[int, list[Path]] = {}
    for cid, stems in by_class.items():
        out[cid] = [stem_to_path[s] for s in stems if s in stem_to_path]
    return out


def _verify_nutrition(names: list[str]) -> None:
    print("\n--- nutrition_table.csv ---")
    if not NUTRITION_CSV.is_file():
        print(f"Missing {NUTRITION_CSV}", file=sys.stderr)
        return
    with NUTRITION_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    have = {r.get("canonical_name", "").strip() for r in rows}
    missing = [n for n in names if n not in have]
    if missing:
        print(f"Missing canonical rows for: {missing}")
    else:
        print(f"All {len(names)} classes present in nutrition_table.csv.")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS, help="best.pt path")
    ap.add_argument("--data", type=Path, default=DEFAULT_DATA, help="dataset yaml")
    ap.add_argument(
        "--project",
        type=Path,
        default=BACKEND_ROOT / "runs" / "detect" / "exp1",
        help="run dir (for eval_viz output)",
    )
    ap.add_argument("--name", type=str, default="eval_viz", help="subfolder under project for viz")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    data_yaml = args.data.resolve()
    weights = args.weights.resolve()
    if not data_yaml.is_file():
        print(f"Data yaml not found: {data_yaml}", file=sys.stderr)
        sys.exit(1)
    if not weights.is_file():
        print(f"Weights not found: {weights}", file=sys.stderr)
        sys.exit(1)

    names = _load_names_from_data_yaml(data_yaml)
    nc = len(names)

    from ultralytics import YOLO

    model = YOLO(str(weights))

    print("\n--- Validation metrics (Ultralytics val, split=val) ---")
    metrics = model.val(data=str(data_yaml), split="val", plots=True, verbose=False)
    box = metrics.box
    map50 = float(box.map50)
    mp = float(box.mp)
    mr = float(box.mr)
    print(f"mAP@0.5: {map50:.4f}")
    print(f"Precision (mean): {mp:.4f}")
    print(f"Recall (mean): {mr:.4f}")
    goal = "PASS" if map50 >= TARGET_MAP50 else "BELOW TARGET"
    print(f"Target mAP@0.5 >= {TARGET_MAP50}: {goal}")

    ap50_arr = box.ap50
    if hasattr(ap50_arr, "tolist"):
        ap50_list = ap50_arr.tolist()
    else:
        ap50_list = list(ap50_arr)

    pairs = [(names[i], float(ap50_list[i])) for i in range(min(nc, len(ap50_list)))]
    pairs.sort(key=lambda x: x[1], reverse=True)

    print("\n--- Per-class AP@0.5 (high to low) ---")
    for name, apv in pairs:
        flag = "  [WARN AP<0.50]" if apv < WARN_AP50 else ""
        print(f"  {name}: {apv:.4f}{flag}")

    _verify_nutrition(names)

    print("\n--- Test-set visualization (random 3 / class if available) ---")
    random.seed(args.seed)
    by_cls = _collect_test_images_by_class(data_yaml)
    out_dir = (args.project / args.name).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    for cid in range(nc):
        paths = by_cls.get(cid, [])
        if not paths:
            print(f"  class {cid} ({names[cid]}): no labeled test images, skip")
            continue
        k = min(SAMPLES_PER_CLASS, len(paths))
        chosen = random.sample(paths, k=k)
        for p in chosen:
            results = model.predict(source=str(p), imgsz=640, save=False, verbose=False)
            for r in results:
                im = r.plot()
                out_path = out_dir / f"{names[cid]}_{p.stem}.jpg"
                cv2.imwrite(str(out_path), im)
    print(f"Saved annotated images to {out_dir}/")


if __name__ == "__main__":
    main()
