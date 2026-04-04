# Phase 1 — Analysis Report / 阶段一分析报告

**Project:** Ingredient-Based Nutritional Estimation  
**Phase title (repository):** Dataset preprocessing and YOLOv8 detection training  
**Date:** March 2026  

---

## 1. Objective / 目标

Build a **10-class raw-ingredient detector** from two Roboflow YOLO exports, unify labels, stratified split, targeted augmentation for underrepresented classes, train **YOLOv8m**, evaluate on val/test, and attach **per-100g USDA-oriented nutrition** rows for downstream demo (Level 1: detect class → lookup macros).

---

## 2. Data pipeline / 数据流程

| Step | Script | Output |
|------|--------|--------|
| Filter & remap | `scripts/filter_classes.py` | `data/filtered/` |
| 80/10/10 multilabel split | `scripts/split_dataset.py` | `data/splits/{train,val,test}/`, `data/dataset.yaml`, `data/splits/data.yaml` |
| Augment (broccoli, cucumber) | `scripts/augment.py` | `data/augmented/train/` |
| Nutrition table | `scripts/build_nutrition_table.py` | `data/nutrition_table.csv` |

Class definitions: `configs/classes.yaml` (`nc: 10`, garlic/chilli excluded).

---

## 3. Training / 训练

- **Entry:** `python models/train_detect.py` (from `backend/`)  
- **Config:** `configs/train_detect.yaml` (model `yolov8m.pt`, epochs, batch, optimizer, etc.)  
- **Data YAML:** `data/splits/data.yaml` — `train` includes both `splits/train` and `augmented/train`; `val`/`test` from `splits` only.  
- **Weights / logs:** **not** committed to Git (see `.gitignore`: `runs/`, `*.pt`). Local output path documented in root `README.md`.

---

## 4. Evaluation snapshot (representative) / 评估结果摘要

Run: `python models/evaluate.py` (default weights: `runs/detect/exp1/weights/best.pt` after training).

| Metric | Value (val) |
|--------|-------------|
| mAP@0.5 | ~0.954 |
| Mean Precision | ~0.957 |
| Mean Recall | ~0.901 |
| Target mAP@0.5 ≥ 0.60 | **PASS** |

Per-class AP@0.5 (example run): strongest classes ~0.95–0.99; **cucumber** lowest in this snapshot (~0.76) but still above typical 0.5 warning threshold.

**Note:** Exact numbers depend on split seed and run; re-run `evaluate.py` after each training for current figures.

---

## 5. Deliverables in repo / 仓库内交付物

- Configs, scripts, dataset YAML stubs, `nutrition_table.csv` schema  
- `Visualization/index.html` — dashboard-style summary (paths to `backend/runs/detect/…` for local charts; not committed).  
- **Not** in Git: trained `.pt` files, `runs/` contents, raw images under `data/raw/`, `filtered/`, `splits/{train,val,test}/` image blobs.

---

## 6. Limitations & next steps / 局限与后续

- 本报告阶段以 **Level 1 检测 + 每 100 g 营养查询** 为主。  
- **仓库当前状态（代码）**：已增加实例分割训练入口、掩码/框面积比估重、`nutrition/` 模块、`models/inference.py` 与 `api/main.py`（详见根目录 `README.md`、`Documents/workspace_doc.md`、`Documents/api_doc.md`）。估重仍为启发式，精度受参考克重与拍摄条件限制。  
- 分割与端到端营养指标的固定数字需在本地 `runs/segment/...` 与 `yolo segment val` 中记录，不随 Git 提交。

---

## References / 参考

- Ultralytics YOLOv8: https://docs.ultralytics.com/  
- USDA FoodData Central (nutrition hints in `nutrition_table.csv`).
