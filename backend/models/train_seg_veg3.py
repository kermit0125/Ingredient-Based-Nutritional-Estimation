from __future__ import annotations

import sys
from pathlib import Path

import torch
import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_ROOT / "configs" / "train_seg_veg3.yaml"


def _resolve_path(p: str | Path) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path.resolve()
    return (BACKEND_ROOT / path).resolve()


def main() -> None:
    if not CONFIG_PATH.is_file():
        print(f"Missing config: {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        print("train_seg_veg3.yaml must be a mapping", file=sys.stderr)
        sys.exit(1)

    model_name = cfg.get("model")
    data_rel = cfg.get("data")
    if not model_name or not data_rel:
        print("Config must define 'model' and 'data'", file=sys.stderr)
        sys.exit(1)

    if not torch.cuda.is_available():
        print("CUDA is not available. Training requires a GPU with CUDA.", file=sys.stderr)
        sys.exit(1)

    data_path = _resolve_path(data_rel)
    if not data_path.is_file():
        print(f"Dataset yaml not found: {data_path}", file=sys.stderr)
        print("Run: python scripts/prepare_veg_seg3_dataset.py", file=sys.stderr)
        sys.exit(1)

    train_kwargs = {k: v for k, v in cfg.items() if k != "model"}
    train_kwargs["data"] = str(data_path)

    proj = train_kwargs.get("project", "runs/segment_veg3")
    if proj and not Path(str(proj)).is_absolute():
        train_kwargs["project"] = str((BACKEND_ROOT / proj).resolve())

    from ultralytics import YOLO

    model_path = _resolve_path(model_name)
    model_arg = str(model_path) if model_path.is_file() else str(model_name)
    model = YOLO(model_arg)
    model.train(**train_kwargs)

    project = Path(str(train_kwargs.get("project", str(BACKEND_ROOT / "runs/segment_veg3"))))
    if not project.is_absolute():
        project = (BACKEND_ROOT / project).resolve()
    name = str(train_kwargs.get("name", "veg3_seg"))
    best = (project / name / "weights" / "best.pt").resolve()
    print(f"Training finished. best.pt: {best}")


if __name__ == "__main__":
    main()
