from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dataset_common import (
    BACKEND_ROOT,
    CONFIG_PATH,
    ensure_augmented_train_dirs,
    load_classes_config,
    write_training_dataset_yaml,
)


def stems_with_pair(images_dir: Path, labels_dir: Path) -> list[str]:
    stems: list[str] = []
    for lab in sorted(labels_dir.glob("*.txt")):
        stem = lab.stem
        exts = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"]
        found = False
        for ext in exts:
            if (images_dir / f"{stem}{ext}").is_file():
                found = True
                break
        if not found:
            for p in images_dir.iterdir():
                if p.is_file() and p.stem == stem:
                    found = True
                    break
        if found:
            stems.append(stem)
        else:
            print(f"[warn] label without image, skipped stem={stem}", file=sys.stderr)
    return stems


def label_vector_for_stem(labels_dir: Path, stem: str, nc: int) -> np.ndarray:
    vec = np.zeros((nc,), dtype=np.int8)
    p = labels_dir / f"{stem}.txt"
    text = p.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        try:
            cid = int(float(parts[0]))
        except (ValueError, IndexError):
            continue
        if 0 <= cid < nc:
            vec[cid] = 1
    return vec


def resolve_image_path(images_dir: Path, stem: str) -> Path | None:
    exts = [".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"]
    for ext in exts:
        p = images_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for p in images_dir.iterdir():
        if p.is_file() and p.stem == stem:
            return p
    return None


def copy_split(stems: list[str], images_dir: Path, labels_dir: Path, out_root: Path, split: str) -> None:
    oi = out_root / split / "images"
    ol = out_root / split / "labels"
    oi.mkdir(parents=True, exist_ok=True)
    ol.mkdir(parents=True, exist_ok=True)
    for stem in stems:
        img = resolve_image_path(images_dir, stem)
        lab = labels_dir / f"{stem}.txt"
        if img is None or not lab.is_file():
            continue
        shutil.copy2(img, oi / img.name)
        shutil.copy2(lab, ol / f"{stem}.txt")


def write_splits_yaml(out_root: Path, class_cfg: dict) -> None:
    names = class_cfg["names"]
    lines = [
        f"path: {out_root.resolve().as_posix()}",
        "train: train/images",
        "val: val/images",
        "test: test/images",
        f"nc: {class_cfg['nc']}",
        "names:",
    ]
    for k in sorted(int(x) for x in names):
        lines.append(f"  {k}: {names[k]}")
    (out_root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--filtered", type=Path, default=BACKEND_ROOT / "data" / "filtered")
    parser.add_argument("--out", type=Path, default=BACKEND_ROOT / "data" / "splits")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-clean", action="store_true")
    args = parser.parse_args()

    class_cfg = load_classes_config(args.config)
    nc = class_cfg["nc"]

    images_dir = args.filtered / "images"
    labels_dir = args.filtered / "labels"
    if not images_dir.is_dir() or not labels_dir.is_dir():
        raise SystemExit(f"Run filter_classes.py first; missing {images_dir} or {labels_dir}")

    stems = stems_with_pair(images_dir, labels_dir)
    if not stems:
        raise SystemExit("No paired image+label samples found")

    n = len(stems)
    Y = np.stack([label_vector_for_stem(labels_dir, s, nc) for s in stems], axis=0)

    def stratified_three_way() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        mss1 = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.1, random_state=args.seed)
        tv_rel, te_rel = next(mss1.split(np.zeros((n, 1)), Y))
        tv_idx = np.sort(tv_rel)
        te_idx = np.sort(te_rel)
        y_tv = Y[tv_idx]
        mss2 = MultilabelStratifiedShuffleSplit(
            n_splits=1, test_size=1.0 / 9.0, random_state=args.seed + 1
        )
        tr_sub, va_sub = next(mss2.split(np.zeros((len(tv_idx), 1)), y_tv))
        train_idx = tv_idx[np.sort(tr_sub)]
        val_idx = tv_idx[np.sort(va_sub)]
        return train_idx, val_idx, te_idx

    try:
        train_idx, val_idx, test_idx = stratified_three_way()
    except ValueError as e:
        print(f"[warn] multilabel stratification failed, using random split: {e}", file=sys.stderr)
        rng = np.random.RandomState(args.seed)
        perm = rng.permutation(n)
        n_test = max(1, int(round(0.1 * n)))
        n_val = max(1, int(round(0.1 * n)))
        test_idx = np.sort(perm[:n_test])
        val_idx = np.sort(perm[n_test : n_test + n_val])
        train_idx = np.sort(perm[n_test + n_val :])

    out_root = args.out.resolve()
    if not args.no_clean and out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    train_stems = [stems[i] for i in train_idx]
    val_stems = [stems[i] for i in val_idx]
    test_stems = [stems[i] for i in test_idx]

    copy_split(train_stems, images_dir, labels_dir, out_root, "train")
    copy_split(val_stems, images_dir, labels_dir, out_root, "val")
    copy_split(test_stems, images_dir, labels_dir, out_root, "test")

    write_splits_yaml(out_root, class_cfg)

    data_root = BACKEND_ROOT / "data"
    ensure_augmented_train_dirs(data_root)
    ds_yml = write_training_dataset_yaml(data_root, class_cfg)
    print(f"wrote training index {ds_yml} (train = splits/train + augmented/train)")

    def brief_stats(name: str, idx_arr: np.ndarray) -> None:
        sub = Y[idx_arr]
        counts = sub.sum(axis=0).astype(int)
        print(f"{name}: n={len(idx_arr)} images_with_class_per_id={counts.tolist()}")

    print(f"total_samples={n}")
    brief_stats("train", train_idx)
    brief_stats("val", val_idx)
    brief_stats("test", test_idx)
    print(f"wrote {out_root / 'data.yaml'}")


if __name__ == "__main__":
    main()
