from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import albumentations as A
import cv2
import numpy as np

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from veg_seg3_common import (
    BACKEND_ROOT,
    corners_to_yolo_bbox,
    find_image,
    read_label_objects,
    write_dataset_yaml,
    write_label_lines,
    yolo_bbox_to_corners,
)


def _flatten_for_aug(
    objects: list[tuple[str, int, np.ndarray]], w: int, h: int
) -> tuple[list[tuple[float, float]], list[tuple]]:
    kps: list[tuple[float, float]] = []
    meta: list[tuple] = []
    for kind, cid, data in objects:
        if kind == "bbox":
            cx, cy, bw, bh = float(data[0]), float(data[1]), float(data[2]), float(data[3])
            corners = yolo_bbox_to_corners(cx, cy, bw, bh) * np.array([w, h], dtype=np.float64)
            for i in range(4):
                kps.append((float(corners[i, 0]), float(corners[i, 1])))
            meta.append(("bbox4", cid))
        else:
            pts = data * np.array([w, h], dtype=np.float64)
            n = len(pts)
            for i in range(n):
                kps.append((float(pts[i, 0]), float(pts[i, 1])))
            meta.append(("poly", cid, n))
    return kps, meta


def _unflatten_from_aug(
    kps_out: list, meta: list[tuple], w: int, h: int
) -> list[tuple[str, int, np.ndarray]] | None:
    out: list[tuple[str, int, np.ndarray]] = []
    idx = 0
    for m in meta:
        if m[0] == "bbox4":
            cid = m[1]
            chunk = np.array(kps_out[idx : idx + 4], dtype=np.float64)
            idx += 4
            if chunk.shape[0] < 4:
                return None
            cx, cy, bw, bh = corners_to_yolo_bbox(chunk, w, h)
            if bw <= 0 or bh <= 0:
                return None
            out.append(("bbox", cid, np.array([cx, cy, bw, bh], dtype=np.float64)))
        else:
            cid, n = m[1], m[2]
            chunk = np.array(kps_out[idx : idx + n], dtype=np.float64)
            idx += n
            if len(chunk) < 3:
                return None
            norm = chunk / np.array([w, h], dtype=np.float64)
            out.append(("poly", cid, norm))
    return out


def build_aug_pipeline() -> A.Compose:
    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.15),
            A.RandomRotate90(p=0.2),
            A.RandomBrightnessContrast(brightness_limit=0.22, contrast_limit=0.22, p=0.55),
            A.HueSaturationValue(hue_shift_limit=10, sat_shift_limit=20, val_shift_limit=16, p=0.45),
            A.MotionBlur(blur_limit=3, p=0.12),
        ],
        keypoint_params=A.KeypointParams(format="xy", remove_invisible=False),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--dataset-root",
        type=Path,
        default=BACKEND_ROOT / "data" / "veg_seg_3class",
    )
    ap.add_argument("--variants", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-clean-aug", action="store_true")
    args = ap.parse_args()

    root = args.dataset_root.resolve()
    train_img = root / "train" / "images"
    train_lab = root / "train" / "labels"
    aug_img = root / "aug_train" / "images"
    aug_lab = root / "aug_train" / "labels"

    if not train_lab.is_dir():
        raise SystemExit(f"Missing {train_lab} — run prepare_veg_seg3_dataset.py first.")

    if aug_img.exists() and not args.no_clean_aug:
        import shutil

        shutil.rmtree(aug_img.parent)
    aug_img.mkdir(parents=True, exist_ok=True)
    aug_lab.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)

    pipe = build_aug_pipeline()
    stems = sorted(p.stem for p in train_lab.glob("*.txt"))
    gen = 0
    for stem in stems:
        lab_path = train_lab / f"{stem}.txt"
        img_path = find_image(train_img, stem)
        if img_path is None:
            continue
        objects = read_label_objects(lab_path)
        if not objects:
            continue
        image = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            continue
        h, w = image.shape[0], image.shape[1]
        kps, meta = _flatten_for_aug(objects, w, h)
        if not kps:
            continue

        for j in range(args.variants):
            random.seed(args.seed + gen * 31 + j * 17)
            np.random.seed(args.seed + gen + j)
            try:
                out = pipe(image=image, keypoints=kps)
            except Exception as e:
                print(f"[warn] aug failed {stem} #{j}: {e}", file=sys.stderr)
                continue
            img2 = out["image"]
            kps2 = out["keypoints"]
            h2, w2 = img2.shape[0], img2.shape[1]
            objs2 = _unflatten_from_aug(kps2, meta, w2, h2)
            if objs2 is None:
                continue
            text = write_label_lines(objs2, w2, h2)
            if not text.strip():
                continue
            new_stem = f"{stem}__aug{j}"
            out_p = aug_img / f"{new_stem}.jpg"
            enc = cv2.imencode(".jpg", img2, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
            if not enc[0]:
                continue
            enc[1].tofile(str(out_p))
            (aug_lab / f"{new_stem}.txt").write_text(text, encoding="utf-8")
            gen += 1

    names_dict = {i: n for i, n in enumerate(["broccoli", "cucumber", "tomato"])}
    write_dataset_yaml(
        root,
        train_image_roots=["train/images", "aug_train/images"],
        nc=3,
        names=names_dict,
    )
    print(f"Wrote {gen} augmented train samples under {root / 'aug_train'}")
    print(f"Updated {root / 'data.yaml'} (train = train/images + aug_train/images)")


if __name__ == "__main__":
    main()
