# Ingredient-Based Nutritional Estimation

**EN:** Ingredient detection and nutritional estimation (course project). This repository holds **configs, data-prep scripts, and docs**. Large image datasets and trained weights are **not** committed; reproduce locally using the links below.

**中文：** 基于食材图像的营养估算（课程项目）。仓库仅包含 **配置、数据处理脚本与文档**；大图与训练权重不纳入版本控制，请按下列链接本地准备数据。

---

## Repository layout

| Path | Purpose |
| --- | --- |
| `backend/configs/` | `classes.yaml` (12 classes + Roboflow name map), `train_detect.yaml` |
| `backend/scripts/` | `filter_classes.py`, `split_dataset.py`, `augment.py`, `dataset_common.py`, `report_class_balance.py` |
| `backend/data/` | `README.md` (bilingual), `DATA_SOURCES.md` (download URLs) — **no** `raw/` / `filtered/` / `splits/` / `augmented/` in git |
| `Documents/` | Workspace notes, API spec, PRD (Chinese) |

Upstream remote: [github.com/kermit0125/Ingredient-Based-Nutritional-Estimation](https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation)

---

## Quick start (data pipeline)

1. Clone the repo and create a venv; install deps:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
2. Download both Roboflow **YOLOv8** zips and extract under `backend/data/raw/` as described in [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md).
3. Run:
   ```bash
   python scripts/filter_classes.py
   python scripts/split_dataset.py
   python scripts/augment.py
   ```
4. Train (example): `yolo detect train model=yolov8m.pt data=data/dataset.yaml` from `backend/`.

Details: [`backend/data/README.md`](backend/data/README.md).

---

## 中文摘要

1. 克隆仓库，`cd backend && pip install -r requirements.txt`。  
2. 按 [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md) 下载两个 YOLOv8 数据集到 `backend/data/raw/`。  
3. 依次运行 `filter_classes.py` → `split_dataset.py` →（可选）`augment.py`。  
4. 使用 `data/dataset.yaml` 训练；说明见 [`backend/data/README.md`](backend/data/README.md)。

---

## GitHub shows no `backend/`? / GitHub 上没有 backend 代码？

**Cause / 原因:** If you ever ran `git init` **inside** `backend/`, that folder gets its own `backend/.git`. The **parent** repository then does **not** track files inside `backend/` (Git treats it as a nested repo).  
若曾在 **`backend` 目录里**执行过 `git init`，会出现 `backend/.git`，上层仓库**不会**把 `backend` 里的脚本提交上去。

**Fix / 修复（在仓库根目录 `Ingredient-Based_Nutritional_Estimation/`）：**

```powershell
# Remove nested git (safe: only removes metadata, not your data/scripts)
Remove-Item -Recurse -Force .\backend\.git

git add backend/configs backend/scripts backend/requirements.txt backend/README.md backend/data/README.md backend/data/DATA_SOURCES.md
git add .gitignore README.md Documents
git status
git commit -m "Track backend configs and scripts in main repository"
git push origin main
```

Or run: `powershell -ExecutionPolicy Bypass -File .\fix_backend_git.ps1` then `git commit` and `git push`.

Always run `git add` / `git commit` from the **repository root**, not from `backend/`.
