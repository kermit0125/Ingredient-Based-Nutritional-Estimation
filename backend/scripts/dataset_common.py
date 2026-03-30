"""Shared helpers: paths, YOLO label I/O, classes.yaml parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_ROOT / "configs" / "classes.yaml"
DATASET_YAML_PATH = BACKEND_ROOT / "data" / "splits" / "data.yaml"

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_classes_config(path: Path | None = None) -> dict:
    p = path or CONFIG_PATH
    cfg = load_yaml(p)
    if not isinstance(cfg, dict):
        raise ValueError(f"Invalid YAML: {p}")
    names_block = cfg.get("names")
    if not isinstance(names_block, dict):
        raise ValueError("classes.yaml must define names as a dict (0: canonical_name)")
    canonical_order = [names_block[i] for i in sorted(int(k) for k in names_block)]
    canonical_to_id = {n: i for i, n in enumerate(canonical_order)}
    return {
        "path": p,
        "nc": int(cfg["nc"]),
        "names": names_block,
        "canonical_order": canonical_order,
        "canonical_to_id": canonical_to_id,
        "sources": cfg.get("sources") or {},
    }


def load_roboflow_names(data_yaml: Path) -> list[str]:
    cfg = load_yaml(data_yaml)
    names = cfg.get("names")
    if isinstance(names, dict):
        return [names[i] for i in sorted(int(k) for k in names)]
    if isinstance(names, list):
        return [str(x) for x in names]
    return []


def read_text_flex(path: Path) -> str | None:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def parse_yolo_label_line(line: str) -> tuple[int, str] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    parts = s.split()
    if len(parts) < 2:
        return None
    try:
        cid = int(float(parts[0]))
    except ValueError:
        return None
    return cid, s


def find_image_for_stem(images_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXTS:
        p = images_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for p in images_dir.iterdir():
        if p.is_file() and p.stem == stem:
            return p
    return None


def label_stems(labels_dir: Path) -> list[str]:
    return sorted(p.stem for p in labels_dir.glob("*.txt"))


def ensure_augmented_train_dirs(data_root: Path | None = None) -> tuple[Path, Path]:
    """Create augmented/train dirs so the second train path in dataset.yaml always exists."""
    root = data_root or (BACKEND_ROOT / "data")
    im = root / "augmented" / "train" / "images"
    lb = root / "augmented" / "train" / "labels"
    im.mkdir(parents=True, exist_ok=True)
    lb.mkdir(parents=True, exist_ok=True)
    return im, lb


def write_training_dataset_yaml(
    data_root: Path | None = None,
    class_cfg: dict | None = None,
    config_path: Path | None = None,
) -> Path:
    """
    Write data/dataset.yaml and data/splits/data.yaml.
    Omit explicit path: Ultralytics uses the yaml file's parent as dataset root (see check_det_dataset).
    - data/dataset.yaml: root = backend/data/
    - data/splits/data.yaml: root = backend/data/splits/, train/val use ../ to reach splits/ and augmented/.
    """
    root = (data_root or (BACKEND_ROOT / "data")).resolve()
    cfg = class_cfg if class_cfg is not None else load_classes_config(config_path)
    names = cfg["canonical_order"]
    nc = cfg["nc"]

    lines_root = [
        "# YOLO Ultralytics — yaml 位于 backend/data/，省略 path 则根目录为本文件目录。",
        "# train: splits 原始 + augmented 增补。",
        "train:",
        "  - splits/train/images",
        "  - augmented/train/images",
        "val: splits/val/images",
        "test: splits/test/images",
        f"nc: {nc}",
        "names:",
    ]
    for n in names:
        lines_root.append(f"  - {n}")
    (root / "dataset.yaml").write_text("\n".join(lines_root) + "\n", encoding="utf-8")

    lines_splits = [
        "# Ultralytics 唯一推荐入口：yaml 位于 backend/data/splits/，根目录 = data/splits/。",
        "train:",
        "  - ../splits/train/images",
        "  - ../augmented/train/images",
        "val: ../splits/val/images",
        "test: ../splits/test/images",
        f"nc: {nc}",
        "names:",
    ]
    for n in names:
        lines_splits.append(f"  - {n}")
    splits_dir = root / "splits"
    splits_dir.mkdir(parents=True, exist_ok=True)
    out = splits_dir / "data.yaml"
    out.write_text("\n".join(lines_splits) + "\n", encoding="utf-8")
    return out
