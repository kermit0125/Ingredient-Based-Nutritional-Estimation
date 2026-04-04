from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dataset_common import BACKEND_ROOT, CONFIG_PATH, load_classes_config


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def bbox_to_polygon_line(cls: int, cx: float, cy: float, w: float, h: float) -> str:
    cx, cy, w, h = float(cx), float(cy), float(w), float(h)
    x1, y1 = cx - w / 2, cy - h / 2
    x2, y2 = cx + w / 2, cy - h / 2
    x3, y3 = cx + w / 2, cy + h / 2
    x4, y4 = cx - w / 2, cy + h / 2
    coords = [_clip01(x1), _clip01(y1), _clip01(x2), _clip01(y2), _clip01(x3), _clip01(y3), _clip01(x4), _clip01(y4)]
    return f"{cls} " + " ".join(f"{c:.6f}" for c in coords)


def convert_label_text(text: str) -> str:
    out_lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            cls = int(float(parts[0]))
        except ValueError:
            continue
        rest = len(parts) - 1
        if rest == 4:
            try:
                cx, cy, w, h = (float(parts[1]), float(parts[2]), float(parts[3]), float(parts[4]))
            except ValueError:
                continue
            out_lines.append(bbox_to_polygon_line(cls, cx, cy, w, h))
        elif rest >= 6 and rest % 2 == 0:
            out_lines.append(line)
        else:
            print(f"[warn] skip invalid label line: {line[:80]}", file=sys.stderr)
    return "\n".join(out_lines) + ("\n" if out_lines else "")


def copy_split_images_labels(
    src_root: Path,
    dst_root: Path,
    split: str,
) -> None:
    sim = src_root / split / "images"
    slb = src_root / split / "labels"
    dim = dst_root / split / "images"
    dlb = dst_root / split / "labels"
    if not sim.is_dir() or not slb.is_dir():
        return
    dim.mkdir(parents=True, exist_ok=True)
    dlb.mkdir(parents=True, exist_ok=True)
    for lab in sorted(slb.glob("*.txt")):
        text = lab.read_text(encoding="utf-8", errors="replace")
        new_text = convert_label_text(text)
        stem = lab.stem
        img = None
        for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"):
            p = sim / f"{stem}{ext}"
            if p.is_file():
                img = p
                break
        if img is None:
            for p in sim.iterdir():
                if p.is_file() and p.stem == stem:
                    img = p
                    break
        if img is None:
            continue
        shutil.copy2(img, dim / img.name)
        (dlb / f"{stem}.txt").write_text(new_text, encoding="utf-8")


def write_seg_dataset_yaml(dst_root: Path, class_cfg: dict, train_extra: list[str] | None = None) -> None:
    names = class_cfg["names"]
    lines = [
        f"path: {dst_root.resolve().as_posix()}",
    ]
    train_extra = train_extra or []
    if train_extra:
        lines.append("train:")
        lines.append("  - train/images")
        for p in train_extra:
            lines.append(f"  - {p}")
    else:
        lines.append("train: train/images")
    lines.extend(
        [
            "val: val/images",
            "test: test/images",
            f"nc: {class_cfg['nc']}",
            "names:",
        ]
    )
    for k in sorted(int(x) for x in names):
        lines.append(f"  {k}: {names[k]}")
    (dst_root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert_augmented_train(src_aug: Path, dst_aug: Path) -> bool:
    sim = src_aug / "images"
    slb = src_aug / "labels"
    if not sim.is_dir() or not slb.is_dir():
        return False
    dim = dst_aug / "images"
    dlb = dst_aug / "labels"
    dim.mkdir(parents=True, exist_ok=True)
    dlb.mkdir(parents=True, exist_ok=True)
    n = 0
    for lab in sorted(slb.glob("*.txt")):
        text = lab.read_text(encoding="utf-8", errors="replace")
        new_text = convert_label_text(text)
        stem = lab.stem
        img = None
        for ext in (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"):
            p = sim / f"{stem}{ext}"
            if p.is_file():
                img = p
                break
        if img is None:
            for p in sim.iterdir():
                if p.is_file() and p.stem == stem:
                    img = p
                    break
        if img is None:
            continue
        shutil.copy2(img, dim / img.name)
        (dlb / f"{stem}.txt").write_text(new_text, encoding="utf-8")
        n += 1
    return n > 0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits-in", type=Path, default=BACKEND_ROOT / "data" / "splits")
    ap.add_argument("--out", type=Path, default=BACKEND_ROOT / "data" / "splits_seg")
    ap.add_argument("--config", type=Path, default=CONFIG_PATH)
    ap.add_argument("--include-augmented", action="store_true")
    ap.add_argument("--no-clean", action="store_true")
    args = ap.parse_args()

    src = args.splits_in.resolve()
    dst = args.out.resolve()
    if not (src / "train" / "images").is_dir():
        raise SystemExit(f"Missing splits train images: {src / 'train' / 'images'} — run split_dataset.py first.")

    class_cfg = load_classes_config(args.config)

    if dst.exists() and not args.no_clean:
        shutil.rmtree(dst)
    dst.mkdir(parents=True, exist_ok=True)

    for split in ("train", "val", "test"):
        copy_split_images_labels(src, dst, split)

    train_extra: list[str] = []
    if args.include_augmented:
        aug_src = BACKEND_ROOT / "data" / "augmented" / "train"
        aug_dst = BACKEND_ROOT / "data" / "augmented_seg" / "train"
        if convert_augmented_train(aug_src, aug_dst):
            train_extra.append("../augmented_seg/train/images")

    write_seg_dataset_yaml(dst, class_cfg, train_extra=train_extra or None)
    print(f"Wrote segmentation-format dataset: {dst / 'data.yaml'}")
    if train_extra:
        print(f"Extra train roots: {train_extra}")


if __name__ == "__main__":
    main()
