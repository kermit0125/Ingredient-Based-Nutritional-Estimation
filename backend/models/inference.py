from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

BACKEND_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS = BACKEND_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from dataset_common import load_classes_config
from nutrition.nutrition_calculator import load_nutrition_table, macros_for_weight
from nutrition.weight_estimator import estimate_weight_from_mask_area

DEFAULT_SEG_WEIGHTS = BACKEND_ROOT / "runs" / "segment" / "exp1" / "weights" / "best.pt"

_nutrition_cache: Any = None


def _nutrition_table():
    global _nutrition_cache
    if _nutrition_cache is None:
        _nutrition_cache = load_nutrition_table()
    return _nutrition_cache


def _mask_area_px(r, idx: int, w: int, h: int) -> int:
    if r.masks is not None and r.masks.xy is not None and idx < len(r.masks.xy):
        xy = r.masks.xy[idx]
        if xy is not None and len(xy) >= 3:
            mask = np.zeros((h, w), dtype=np.uint8)
            pts = np.asarray(xy, dtype=np.float32)
            pts = np.round(pts).astype(np.int32)
            pts[:, 0] = np.clip(pts[:, 0], 0, w - 1)
            pts[:, 1] = np.clip(pts[:, 1], 0, h - 1)
            cv2.fillPoly(mask, [pts], 1)
            return int(mask.sum())

    if r.boxes is None or idx >= len(r.boxes.xyxy):
        return 0
    box = r.boxes.xyxy[idx].cpu().numpy()
    x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
    x1, y1 = max(0, int(round(x1))), max(0, int(round(y1)))
    x2, y2 = min(w - 1, int(round(x2))), min(h - 1, int(round(y2)))
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def run_predict(
    image_bgr: np.ndarray,
    *,
    weights: Path,
    conf: float = 0.5,
) -> dict[str, Any]:
    if image_bgr.ndim != 3 or image_bgr.shape[2] != 3:
        raise ValueError("image_bgr must be HxWx3 BGR")

    h, w = int(image_bgr.shape[0]), int(image_bgr.shape[1])
    names = load_classes_config()["canonical_order"]
    table = _nutrition_table()

    from ultralytics import YOLO

    model = YOLO(str(weights.resolve()))
    results = model.predict(source=image_bgr, conf=conf, save=False, verbose=False)
    r = results[0]

    if r.boxes is None or len(r.boxes) == 0:
        _, buf = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return {
            "ingredients": [],
            "totals": {"calories": 0.0, "carbs_g": 0.0, "protein_g": 0.0, "fat_g": 0.0},
            "annotated_image_base64": base64.b64encode(buf.tobytes()).decode("ascii"),
            "message": "未识别到支持的食材，请尝试换一张图片",
        }

    confs = r.boxes.conf.cpu().numpy()
    clss = r.boxes.cls.cpu().numpy().astype(int)
    xyxy = r.boxes.xyxy.cpu().numpy()

    order = sorted(range(len(confs)), key=lambda i: float(confs[i]), reverse=True)

    ingredients: list[dict[str, Any]] = []
    tot_c = tot_cb = tot_p = tot_f = 0.0

    for i in order:
        cid = int(clss[i])
        if not (0 <= cid < len(names)):
            continue
        cname = names[cid]
        cf = float(confs[i])
        if cf < conf:
            continue

        area_px = _mask_area_px(r, i, w, h)
        if area_px <= 0:
            continue

        west = estimate_weight_from_mask_area(area_px, w, h, cname)
        if west is None:
            continue

        x1, y1, x2, y2 = xyxy[i]
        bbox = [int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))]

        item: dict[str, Any] = {
            "class": cname,
            "confidence": round(cf, 4),
            "bbox": bbox,
            "mask_area_ratio": round(west.mask_area_ratio, 6),
            "estimated_weight_g": round(west.estimated_weight_g, 2),
        }
        if west.estimate_note:
            item["estimate_note"] = west.estimate_note

        macros = macros_for_weight(table, cname, west.estimated_weight_g)
        if macros is None:
            item["calories"] = 0.0
            item["carbs_g"] = 0.0
            item["protein_g"] = 0.0
            item["fat_g"] = 0.0
            item["estimate_note"] = (item.get("estimate_note") or "") + "；营养数据缺失"
        else:
            item["calories"] = macros["calories"]
            item["carbs_g"] = macros["carbs_g"]
            item["protein_g"] = macros["protein_g"]
            item["fat_g"] = macros["fat_g"]
            tot_c += macros["calories"]
            tot_cb += macros["carbs_g"]
            tot_p += macros["protein_g"]
            tot_f += macros["fat_g"]

        ingredients.append(item)

    plotted = r.plot(img=image_bgr, masks=True, boxes=True, labels=True)
    _, buf = cv2.imencode(".jpg", plotted, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")

    if not ingredients:
        _, buf0 = cv2.imencode(".jpg", image_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        return {
            "ingredients": [],
            "totals": {"calories": 0.0, "carbs_g": 0.0, "protein_g": 0.0, "fat_g": 0.0},
            "annotated_image_base64": base64.b64encode(buf0.tobytes()).decode("ascii"),
            "message": "未识别到支持的食材，请尝试换一张图片",
        }

    return {
        "ingredients": ingredients,
        "totals": {
            "calories": round(tot_c, 2),
            "carbs_g": round(tot_cb, 3),
            "protein_g": round(tot_p, 3),
            "fat_g": round(tot_f, 3),
        },
        "annotated_image_base64": b64,
        "message": None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=Path, required=True)
    ap.add_argument("--weights", type=Path, default=DEFAULT_SEG_WEIGHTS)
    ap.add_argument("--conf", type=float, default=0.5)
    args = ap.parse_args()

    wpath = args.weights.resolve()
    if not wpath.is_file():
        print(f"Weights not found: {wpath}", file=sys.stderr)
        sys.exit(1)
    img_path = args.image.resolve()
    if not img_path.is_file():
        print(f"Image not found: {img_path}", file=sys.stderr)
        sys.exit(1)

    im = cv2.imread(str(img_path))
    if im is None:
        print(f"Failed to read image: {img_path}", file=sys.stderr)
        sys.exit(1)

    out = run_predict(im, weights=wpath, conf=args.conf)
    print("ingredients:", len(out["ingredients"]))
    for i, ing in enumerate(out["ingredients"], 1):
        line = (
            f"  [{i}] {ing['class']}  "
            f"估重≈{ing['estimated_weight_g']} g  "
            f"(面积比={ing['mask_area_ratio']}, 置信度={ing['confidence']})"
        )
        print(line)
        if ing.get("estimate_note"):
            print(f"      备注: {ing['estimate_note']}")
    if out["ingredients"]:
        wsum = sum(float(x["estimated_weight_g"]) for x in out["ingredients"])
        print(f"估重合计: {wsum:.2f} g")
    print("totals:", out["totals"])
    if out.get("message"):
        print("message:", out["message"])


if __name__ == "__main__":
    main()
