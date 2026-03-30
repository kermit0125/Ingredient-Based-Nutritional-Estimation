"""
Level 1 推理演示：单张图 -> 带框的标注图 + 每个检测类别的每 100g 营养值（来自 nutrition_table.csv）。

从 backend/ 运行:
    python models/demo_inference.py --image path/to.jpg
    python models/demo_inference.py --image path/to.jpg --weights runs/detect/exp1/weights/best.pt
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2

BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = BACKEND_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dataset_common import load_classes_config  # noqa: E402

DEFAULT_WEIGHTS = BACKEND_ROOT / "runs" / "detect" / "exp1" / "weights" / "best.pt"
NUTRITION_CSV = BACKEND_ROOT / "data" / "nutrition_table.csv"


def _load_nutrition() -> dict[str, dict[str, float]]:
    if not NUTRITION_CSV.is_file():
        raise FileNotFoundError(f"Missing {NUTRITION_CSV}")
    out: dict[str, dict[str, float]] = {}
    with NUTRITION_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("canonical_name") or "").strip()
            if not name:
                continue
            out[name] = {
                "calories_kcal": float(row["calories_kcal"]),
                "carbohydrate_g": float(row["carbohydrate_g"]),
                "protein_g": float(row["protein_g"]),
                "fat_g": float(row["fat_g"]),
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    ap.add_argument("--out", type=Path, default=None, help="output image path")
    args = ap.parse_args()

    img_path = args.image.resolve()
    wpath = args.weights.resolve()
    if not img_path.is_file():
        print(f"Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)
    if not wpath.is_file():
        print(f"Weights not found: {wpath}", file=sys.stderr)
        sys.exit(1)

    names = load_classes_config()["canonical_order"]
    nutrition = _load_nutrition()

    from ultralytics import YOLO

    model = YOLO(str(wpath))
    results = model.predict(source=str(img_path), save=False, verbose=False)
    r = results[0]
    im = r.plot()

    y0 = 24
    for b in r.boxes:
        cid = int(b.cls[0].item())
        if 0 <= cid < len(names):
            cname = names[cid]
            row = nutrition.get(cname)
            if row is None:
                line = f"{cname}: (no nutrition row)"
            else:
                line = (
                    f"{cname}: {row['calories_kcal']:.0f} kcal / 100g "
                    f"P {row['protein_g']:.1f}g C {row['carbohydrate_g']:.1f}g F {row['fat_g']:.1f}g"
                )
            cv2.putText(
                im,
                line,
                (8, y0),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (0, 0, 0),
                3,
                cv2.LINE_AA,
            )
            cv2.putText(
                im,
                line,
                (8, y0),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )
            y0 += 18

    out = args.out
    if out is None:
        out = img_path.parent / f"{img_path.stem}_demo{img_path.suffix}"
    else:
        out = out.resolve()
    cv2.imwrite(str(out), im)
    print(f"Saved: {out}")


if __name__ == "__main__":
    main()
