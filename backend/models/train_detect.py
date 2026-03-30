"""
YOLO 检测训练入口：仅读取 configs/train_detect.yaml，不在此硬编码超参数。

从 backend/ 目录运行:
    python models/train_detect.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
import yaml

BACKEND_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = BACKEND_ROOT / "configs" / "train_detect.yaml"


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
        print("train_detect.yaml must be a mapping", file=sys.stderr)
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
        sys.exit(1)

    train_kwargs = {k: v for k, v in cfg.items() if k != "model"}
    train_kwargs["data"] = str(data_path)

    # Ultralytics 将相对路径的 project 解析为「当前工作目录」相对路径，会导致在错误 cwd 下
    # 出现 runs/detect/runs/detect/... 嵌套。统一锚定到 backend/ 根目录。
    proj = train_kwargs.get("project", "runs/detect")
    if proj and not Path(str(proj)).is_absolute():
        train_kwargs["project"] = str((BACKEND_ROOT / proj).resolve())

    from ultralytics import YOLO

    model_path = _resolve_path(model_name)
    model_arg = str(model_path) if model_path.is_file() else str(model_name)
    model = YOLO(model_arg)
    model.train(**train_kwargs)

    project = Path(str(train_kwargs.get("project", str(BACKEND_ROOT / "runs/detect"))))
    if not project.is_absolute():
        project = (BACKEND_ROOT / project).resolve()
    name = str(train_kwargs.get("name", "exp"))
    best = (project / name / "weights" / "best.pt").resolve()
    print(f"Training finished. best.pt: {best}")


if __name__ == "__main__":
    main()
