from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent

IMG_EXTS = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")


def load_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def roboflow_class_names(data_yaml: Path) -> list[str]:
    cfg = load_yaml(data_yaml)
    names = cfg.get("names")
    if isinstance(names, dict):
        return [names[i] for i in sorted(int(k) for k in names)]
    if isinstance(names, list):
        return [str(x) for x in names]
    return []


def find_image(images_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXTS:
        p = images_dir / f"{stem}{ext}"
        if p.is_file():
            return p
    for p in images_dir.iterdir():
        if p.is_file() and p.stem == stem:
            return p
    return None


def parse_yolo_instance_line(line: str) -> tuple[str, int, np.ndarray] | None:
    s = line.strip()
    if not s or s.startswith("#"):
        return None
    parts = s.split()
    if len(parts) < 5:
        return None
    try:
        cid = int(float(parts[0]))
    except ValueError:
        return None
    vals = [float(x) for x in parts[1:]]
    if len(vals) == 4:
        return ("bbox", cid, np.array(vals, dtype=np.float64))
    if len(vals) >= 6 and len(vals) % 2 == 0:
        arr = np.array(vals, dtype=np.float64).reshape(-1, 2)
        return ("poly", cid, arr)
    return None


def yolo_bbox_to_corners(cx: float, cy: float, w: float, h: float) -> np.ndarray:
    x1, y1 = cx - w / 2, cy - h / 2
    x2, y2 = cx + w / 2, cy + h / 2
    return np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float64)


def corners_to_yolo_bbox(corners_px: np.ndarray, w: int, h: int) -> tuple[float, float, float, float]:
    xs = corners_px[:, 0] / float(w)
    ys = corners_px[:, 1] / float(h)
    x1, x2 = float(xs.min()), float(xs.max())
    y1, y2 = float(ys.min()), float(ys.max())
    bw, bh = x2 - x1, y2 - y1
    return (x1 + bw / 2, y1 + bh / 2, bw, bh)


def write_label_lines(
    objects: list[tuple[str, int, np.ndarray]], _img_w: int, _img_h: int
) -> str:
    lines: list[str] = []
    for kind, cid, data in objects:
        if kind == "bbox":
            cx, cy, bw, bh = float(data[0]), float(data[1]), float(data[2]), float(data[3])
            lines.append(f"{cid} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
        else:
            flat = np.asarray(data, dtype=np.float64).flatten()
            lines.append(f"{cid} " + " ".join(f"{x:.6f}" for x in flat))
    return "\n".join(lines) + ("\n" if lines else "")


def read_label_objects(path: Path) -> list[tuple[str, int, np.ndarray]]:
    text = path.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[str, int, np.ndarray]] = []
    for line in text.splitlines():
        p = parse_yolo_instance_line(line)
        if p is not None:
            out.append(p)
    return out


def write_dataset_yaml(
    out_root: Path,
    *,
    train_image_roots: list[str],
    nc: int,
    names: dict[int, str],
) -> None:
    lines = [f"path: {out_root.resolve().as_posix()}", "train:"]
    for tr in train_image_roots:
        lines.append(f"  - {tr}")
    lines.extend(
        [
            "val: val/images",
            "test: test/images",
            f"nc: {nc}",
            "names:",
        ]
    )
    for k in sorted(names):
        lines.append(f"  {k}: {names[k]}")
    (out_root / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")
