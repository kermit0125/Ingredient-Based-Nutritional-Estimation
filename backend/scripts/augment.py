from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import albumentations as A
import cv2
import numpy as np

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dataset_common import (
    BACKEND_ROOT,
    CONFIG_PATH,
    load_classes_config,
    write_training_dataset_yaml,
)


def stems_for_classes(labels_dir: Path, class_ids: set[int]) -> list[str]:
    out: list[str] = []
    for lab in labels_dir.glob("*.txt"):
        text = lab.read_text(encoding="utf-8", errors="replace")
        ids: set[int] = set()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                cid = int(float(line.split()[0]))
            except (ValueError, IndexError):
                continue
            ids.add(cid)
        if ids & class_ids:
            out.append(lab.stem)
    return sorted(set(out))


def count_images_with_class(labels_dir: Path, class_id: int) -> int:
    return len(stems_for_classes(labels_dir, {class_id}))


def read_yolo_labels(path: Path) -> tuple[list[list[float]], list[int]]:
    bbs: list[list[float]] = []
    cls: list[int] = []
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        # Instance-segmentation polygons: class + >= 6 normalized coords (pairs). Skip here — bbox aug cannot warp polygons.
        if len(parts) > 5:
            continue
        try:
            c = int(float(parts[0]))
            bb = [float(x) for x in parts[1:5]]
        except ValueError:
            continue
        cls.append(c)
        bbs.append(bb)
    return bbs, cls


def write_yolo_labels(path: Path, bbs: list, cls: list[int]) -> None:
    lines = []
    for c, bb in zip(cls, bbs):
        bb = [float(x) for x in bb]
        lines.append(f"{int(c)} {bb[0]:.6f} {bb[1]:.6f} {bb[2]:.6f} {bb[3]:.6f}")
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def resolve_image(images_dir: Path, stem: str) -> Path | None:
    for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
        p = images_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for p in images_dir.iterdir():
        if p.is_file() and p.stem == stem:
            return p
    return None


def build_pipeline() -> A.Compose:
    return A.Compose(
        [
            A.HorizontalFlip(p=0.5),
            A.VerticalFlip(p=0.15),
            A.RandomRotate90(p=0.2),
            A.RandomBrightnessContrast(brightness_limit=0.25, contrast_limit=0.25, p=0.6),
            A.HueSaturationValue(hue_shift_limit=12, sat_shift_limit=22, val_shift_limit=18, p=0.5),
            A.GaussNoise(var_limit=(8.0, 48.0), p=0.25),
            A.MotionBlur(blur_limit=3, p=0.15),
        ],
        bbox_params=A.BboxParams(format="yolo", label_fields=["cls"], min_visibility=0.3),
    )


def aug_variants_per_image(
    n_with_class_total: int,
    n_base_images: int,
    target: int,
    min_aug: int,
    max_aug: int,
) -> int:
    if n_base_images <= 0:
        return 0
    if n_with_class_total >= target:
        return 0
    deficit = target - n_with_class_total
    k = int(np.ceil(deficit / float(n_base_images)))
    k = max(min_aug, k)
    return min(max_aug, k)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--train-images", type=Path, default=BACKEND_ROOT / "data" / "splits" / "train" / "images")
    parser.add_argument("--train-labels", type=Path, default=BACKEND_ROOT / "data" / "splits" / "train" / "labels")
    parser.add_argument("--out-images", type=Path, default=BACKEND_ROOT / "data" / "augmented" / "train" / "images")
    parser.add_argument("--out-labels", type=Path, default=BACKEND_ROOT / "data" / "augmented" / "train" / "labels")
    parser.add_argument("--target", type=int, default=160)
    parser.add_argument("--min-aug", type=int, default=3)
    parser.add_argument("--max-aug", type=int, default=6)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--inplace", action="store_true")
    args = parser.parse_args()

    cfg = load_classes_config(args.config)
    order = cfg["canonical_order"]
    try:
        cid_broccoli = order.index("broccoli")
        cid_cucumber = order.index("cucumber")
    except ValueError as e:
        raise SystemExit("classes.yaml must define broccoli and cucumber") from e

    images_dir = args.train_images
    labels_dir = args.train_labels
    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise SystemExit("Run split_dataset.py first; missing train/images or train/labels")

    if args.inplace:
        out_images = images_dir
        out_labels = labels_dir
    else:
        out_images = args.out_images
        out_labels = args.out_labels
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    random.seed(args.seed)
    np.random.seed(args.seed)

    for focus_id, focus_name in [(cid_broccoli, "broccoli"), (cid_cucumber, "cucumber")]:
        stems = stems_for_classes(labels_dir, {focus_id})
        n_base = len(stems)
        if n_base == 0:
            print(f"[skip] {focus_name}: no train samples with this class")
            continue

        n_aug_existing = count_images_with_class(out_labels, focus_id) if out_labels != labels_dir else 0
        if args.inplace:
            n_with_total = count_images_with_class(out_labels, focus_id)
        else:
            n_with_total = n_base + n_aug_existing

        k = aug_variants_per_image(n_with_total, n_base, args.target, args.min_aug, args.max_aug)
        if k == 0:
            print(f"[ok] {focus_name}: already {n_with_total} images with class >= target {args.target}, skip")
            continue

        print(
            f"{focus_name}: approx {n_with_total} images with class (base={n_base}), "
            f"{k} aug per base, target={args.target}"
        )

        pipe = build_pipeline()
        gen = 0
        for stem in stems:
            img_path = resolve_image(images_dir, stem)
            lab_path = labels_dir / f"{stem}.txt"
            if img_path is None or not lab_path.is_file():
                continue
            image = cv2.imdecode(np.fromfile(str(img_path), dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                print(f"[warn] cannot read image: {img_path}", file=sys.stderr)
                continue
            bbs, clss = read_yolo_labels(lab_path)
            if not bbs:
                continue
            for j in range(k):
                random.seed(args.seed + gen * 17 + j * 7919)
                np.random.seed(args.seed + gen + j)
                try:
                    out = pipe(image=image, bboxes=bbs, cls=clss)
                except Exception as e:
                    print(f"[warn] augment failed {stem} #{j}: {e}", file=sys.stderr)
                    continue
                img2 = out["image"]
                bbs2 = out["bboxes"]
                cls2 = out["cls"]
                if not bbs2:
                    continue
                new_stem = f"{stem}__aug{focus_name}_{j}"
                out_img = out_images / f"{new_stem}.jpg"
                n = 0
                while out_img.exists():
                    n += 1
                    new_stem = f"{stem}__aug{focus_name}_{j}_x{n}"
                    out_img = out_images / f"{new_stem}.jpg"
                enc = cv2.imencode(".jpg", img2)
                if not enc[0]:
                    continue
                enc[1].tofile(str(out_img))
                cls_out = [int(x) for x in cls2]
                write_yolo_labels(out_labels / f"{new_stem}.txt", list(bbs2), cls_out)
                gen += 1

        if args.inplace:
            after = count_images_with_class(out_labels, focus_id)
        else:
            after = n_base + count_images_with_class(out_labels, focus_id)
        print(f"{focus_name}: done, approx {after} images with class (target {args.target})")

    write_training_dataset_yaml(BACKEND_ROOT / "data", cfg)
    if not args.inplace:
        print(
            f"augmentation dir: {out_images.parent}; "
            f"refreshed data/dataset.yaml and data/splits/data.yaml (splits/train + augmented/train)."
        )
    else:
        print(
            "refreshed data/dataset.yaml and data/splits/data.yaml "
            "(--inplace: verify you are not double-counting train paths)."
        )


if __name__ == "__main__":
    main()
