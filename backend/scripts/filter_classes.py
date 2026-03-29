"""
Filter two Roboflow YOLOv8 exports to the 12 classes in configs/classes.yaml,
remap IDs to 0..11, merge images + labels into data/filtered/ (ds1_/ds2_ prefixes).

Run from backend/:
    python scripts/filter_classes.py
    python scripts/filter_classes.py --no-clean
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from dataset_common import (
    BACKEND_ROOT,
    CONFIG_PATH,
    find_image_for_stem,
    load_classes_config,
    load_roboflow_names,
    parse_yolo_label_line,
    read_text_flex,
)


def build_raw_id_map(names: list[str], raw_to_canonical: dict, canonical_to_id: dict) -> dict[int, int]:
    """Map raw class index from data.yaml -> unified id."""
    name_to_idx = {n: i for i, n in enumerate(names)}
    out: dict[int, int] = {}
    for raw_name, canonical in raw_to_canonical.items():
        if raw_name not in name_to_idx:
            print(f"[warn] raw class not in data.yaml names, skipped: {raw_name!r}", file=sys.stderr)
            continue
        if canonical not in canonical_to_id:
            print(f"[warn] unknown canonical {canonical!r} (raw={raw_name!r})", file=sys.stderr)
            continue
        rid = name_to_idx[raw_name]
        out[rid] = canonical_to_id[canonical]
    return out


def filter_label_text(text: str, raw_to_unified: dict[int, int]) -> str:
    lines_out: list[str] = []
    for line in text.splitlines():
        parsed = parse_yolo_label_line(line)
        if parsed is None:
            continue
        old_id, full_line = parsed
        if old_id not in raw_to_unified:
            continue
        new_id = raw_to_unified[old_id]
        rest = full_line.split(None, 1)
        tail = rest[1] if len(rest) > 1 else ""
        lines_out.append(f"{new_id} {tail}".strip())
    return "\n".join(lines_out) + ("\n" if lines_out else "")


def process_source(
    source_key: str,
    source_cfg: dict,
    canonical_to_id: dict,
    out_images: Path,
    out_labels: Path,
) -> tuple[int, int, int]:
    """Returns (written_samples, skipped_empty_labels, missing_image)."""
    rel = Path(source_cfg["path"])
    root = (BACKEND_ROOT / rel).resolve()
    data_yaml = root / "data.yaml"
    prefix = str(source_cfg["file_prefix"])
    raw_map = source_cfg.get("raw_to_canonical") or {}

    if not data_yaml.is_file():
        raise FileNotFoundError(f"missing data.yaml: {data_yaml}")

    names = load_roboflow_names(data_yaml)
    raw_to_unified = build_raw_id_map(names, raw_map, canonical_to_id)
    if not raw_to_unified:
        raise RuntimeError(f"{source_key}: no class mapping could be built")

    written = 0
    skipped_empty = 0
    missing_img = 0

    for split in ("train", "valid", "test"):
        labels_dir = root / split / "labels"
        images_dir = root / split / "images"
        if not labels_dir.is_dir() or not images_dir.is_dir():
            continue
        for lab_path in sorted(labels_dir.glob("*.txt")):
            text = read_text_flex(lab_path)
            if text is None:
                continue
            new_text = filter_label_text(text, raw_to_unified)
            if not new_text.strip():
                skipped_empty += 1
                continue
            stem = lab_path.stem
            img_path = find_image_for_stem(images_dir, stem)
            if img_path is None:
                missing_img += 1
                print(f"[warn] no image for label: {images_dir} / {stem}", file=sys.stderr)
                continue
            new_stem = f"{prefix}{stem}"
            out_lab = out_labels / f"{new_stem}.txt"
            out_img = out_images / f"{new_stem}{img_path.suffix.lower()}"

            if out_img.suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}:
                out_img = out_images / f"{new_stem}.jpg"

            n = 0
            while out_img.exists() or out_lab.exists():
                n += 1
                new_stem = f"{prefix}{stem}__dup{n}"
                out_lab = out_labels / f"{new_stem}.txt"
                out_img = out_images / f"{new_stem}{img_path.suffix.lower()}"

            shutil.copy2(img_path, out_img)
            out_lab.write_text(new_text, encoding="utf-8", newline="\n")
            written += 1

    return written, skipped_empty, missing_img


def write_filtered_data_yaml(out_dir: Path, class_cfg: dict) -> None:
    """Write nc/names only; full training paths come from split_dataset + dataset.yaml."""
    names = class_cfg["names"]
    lines = [f"nc: {class_cfg['nc']}", "names:"]
    for k in sorted(int(x) for x in names):
        lines.append(f"  {k}: {names[k]}")
    (out_dir / "data.yaml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter and merge 12 classes into data/filtered/")
    parser.add_argument("--config", type=Path, default=CONFIG_PATH, help="Path to classes.yaml")
    parser.add_argument(
        "--out",
        type=Path,
        default=BACKEND_ROOT / "data" / "filtered",
        help="Output root (contains images/ and labels/)",
    )
    parser.add_argument("--no-clean", action="store_true", help="Do not delete existing filtered/ before run")
    args = parser.parse_args()

    class_cfg = load_classes_config(args.config)
    out_root = args.out.resolve()
    out_images = out_root / "images"
    out_labels = out_root / "labels"

    if not args.no_clean and out_root.exists():
        shutil.rmtree(out_root)
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    sources = class_cfg["sources"]
    if not isinstance(sources, dict):
        raise SystemExit("classes.yaml: invalid sources block")

    total_w = 0
    for key, scfg in sources.items():
        if not isinstance(scfg, dict):
            continue
        w, sk, miss = process_source(key, scfg, class_cfg["canonical_to_id"], out_images, out_labels)
        print(f"{key}: written={w} skipped_empty_labels={sk} missing_image={miss}")
        total_w += w

    write_filtered_data_yaml(out_root, class_cfg)
    print(f"total_written={total_w} output_dir={out_root}")


if __name__ == "__main__":
    main()
