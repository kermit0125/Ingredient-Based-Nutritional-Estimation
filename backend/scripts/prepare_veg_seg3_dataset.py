from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
from iterstrat.ml_stratifiers import MultilabelStratifiedShuffleSplit

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from veg_seg3_common import (
    BACKEND_ROOT,
    find_image,
    roboflow_class_names,
    write_dataset_yaml,
)


CANONICAL = ["broccoli", "cucumber", "tomato"]


def raw_name_to_id(names: list[str], raw_cid: int) -> int:
    if not 0 <= raw_cid < len(names):
        return -1
    n = names[raw_cid]
    key = n.strip().lower()
    mapping = {"broccoli": 0, "cucumber": 1, "tomato": 2}
    return mapping.get(key, -1)


def remap_label_text(text: str, names: list[str]) -> str:
    lines_out: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            old = int(float(parts[0]))
        except ValueError:
            continue
        new_id = raw_name_to_id(names, old)
        if new_id < 0:
            continue
        tail = " ".join(parts[1:])
        lines_out.append(f"{new_id} {tail}")
    return "\n".join(lines_out) + ("\n" if lines_out else "")


def copy_split(
    raw_root: Path,
    split_in: str,
    out_root: Path,
    split_out: str,
    names: list[str],
) -> int:
    sim = raw_root / split_in / "images"
    slb = raw_root / split_in / "labels"
    if not sim.is_dir() or not slb.is_dir():
        return 0
    dim = out_root / split_out / "images"
    dlb = out_root / split_out / "labels"
    dim.mkdir(parents=True, exist_ok=True)
    dlb.mkdir(parents=True, exist_ok=True)
    n = 0
    for lab in sorted(slb.glob("*.txt")):
        text = lab.read_text(encoding="utf-8", errors="replace")
        new_text = remap_label_text(text, names)
        if not new_text.strip():
            continue
        stem = lab.stem
        img = find_image(sim, stem)
        if img is None:
            print(f"[warn] no image for {sim}/{stem}", file=sys.stderr)
            continue
        shutil.copy2(img, dim / img.name)
        (dlb / f"{stem}.txt").write_text(new_text, encoding="utf-8")
        n += 1
    return n


def collect_all_stems(raw_root: Path, names: list[str]) -> tuple[list[str], Path, Path]:
    stems_set: set[str] = set()
    src_images: dict[str, Path] = {}
    src_labels: dict[str, Path] = {}
    for split in ("train", "valid", "test"):
        sim = raw_root / split / "images"
        slb = raw_root / split / "labels"
        if not slb.is_dir():
            continue
        for lab in slb.glob("*.txt"):
            stem = lab.stem
            img = find_image(sim, stem) if sim.is_dir() else None
            if img is None:
                continue
            text = lab.read_text(encoding="utf-8", errors="replace")
            if not remap_label_text(text, names).strip():
                continue
            stems_set.add(stem)
            src_images[stem] = img
            src_labels[stem] = lab
    stems = sorted(stems_set)
    return stems, src_images, src_labels


def label_vector(path: Path, names: list[str]) -> np.ndarray:
    vec = np.zeros((3,), dtype=np.int8)
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            cid = int(float(parts[0]))
        except ValueError:
            continue
        nid = raw_name_to_id(names, cid)
        if 0 <= nid < 3:
            vec[nid] = 1
    return vec


def resplit_copy(
    raw_root: Path,
    out_root: Path,
    names: list[str],
    seed: int,
) -> None:
    stems, src_images, src_labels = collect_all_stems(raw_root, names)
    if not stems:
        raise SystemExit("No labeled samples found under raw train/valid/test.")

    Y = np.stack([label_vector(src_labels[s], names) for s in stems], axis=0)
    n = len(stems)
    mss1 = MultilabelStratifiedShuffleSplit(n_splits=1, test_size=0.1, random_state=seed)
    train_val_idx, test_idx = next(mss1.split(np.zeros((n, 1)), Y))
    train_val_idx = np.sort(train_val_idx)
    test_idx = np.sort(test_idx)
    y_tv = Y[train_val_idx]
    mss2 = MultilabelStratifiedShuffleSplit(
        n_splits=1, test_size=1.0 / 9.0, random_state=seed + 1
    )
    tr_sub, va_sub = next(mss2.split(np.zeros((len(train_val_idx), 1)), y_tv))
    train_idx = train_val_idx[np.sort(tr_sub)]
    val_idx = train_val_idx[np.sort(va_sub)]

    def dump(idx_arr: np.ndarray, split: str) -> int:
        oi = out_root / split / "images"
        ol = out_root / split / "labels"
        oi.mkdir(parents=True, exist_ok=True)
        ol.mkdir(parents=True, exist_ok=True)
        c = 0
        for i in idx_arr:
            stem = stems[int(i)]
            img = src_images[stem]
            lab = src_labels[stem]
            text = lab.read_text(encoding="utf-8", errors="replace")
            new_text = remap_label_text(text, names)
            shutil.copy2(img, oi / img.name)
            (ol / f"{stem}.txt").write_text(new_text, encoding="utf-8")
            c += 1
        return c

    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    nt = dump(train_idx, "train")
    nv = dump(val_idx, "val")
    nte = dump(test_idx, "test")
    print(f"resplit: train={nt} val={nv} test={nte} (total {n})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--raw",
        type=Path,
        default=BACKEND_ROOT / "data" / "raw" / "Vegetables.v5-danya.yolov8",
    )
    ap.add_argument("--out", type=Path, default=BACKEND_ROOT / "data" / "veg_seg_3class")
    ap.add_argument("--resplit", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-clean", action="store_true")
    args = ap.parse_args()

    raw_root = args.raw.resolve()
    data_yaml = raw_root / "data.yaml"
    if not data_yaml.is_file():
        raise SystemExit(f"Missing {data_yaml}")

    names = roboflow_class_names(data_yaml)
    if len(names) != 3:
        print(f"[warn] expected 3 classes in raw data.yaml, got {names}", file=sys.stderr)

    out_root = args.out.resolve()
    if out_root.exists() and not args.no_clean:
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    if args.resplit:
        resplit_copy(raw_root, out_root, names, args.seed)
    else:
        n_tr = copy_split(raw_root, "train", out_root, "train", names)
        n_va = copy_split(raw_root, "valid", out_root, "val", names)
        n_te = copy_split(raw_root, "test", out_root, "test", names)
        print(f"copied: train={n_tr} val={n_va} test={n_te}")

    names_dict = {i: CANONICAL[i] for i in range(3)}
    write_dataset_yaml(out_root, train_image_roots=["train/images"], nc=3, names=names_dict)
    print(f"Wrote {out_root / 'data.yaml'}")


if __name__ == "__main__":
    main()
