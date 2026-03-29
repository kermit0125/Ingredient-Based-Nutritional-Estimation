# Ingredient-Based Nutritional Estimation

## About / 项目简介

**English:** Course project **INE (Ingredient Nutrition Estimator)** — estimate macros and calories from photos of raw ingredients. The stack targets **YOLOv8 detection** (and later segmentation) plus a **FastAPI** backend and a separate web frontend. This repo ships **configs, offline data-prep scripts, and product/API docs**; large image sets and model weights stay local.

**中文：** 课程项目「食材营养识别」：用户拍摄**烹饪前生鲜食材**，系统识别类别、估计份量并输出碳水/蛋白/脂肪与热量。技术路线为 **YOLOv8 检测**（后续可接分割）+ **FastAPI** + 前端。本仓库包含**配置、离线数据处理脚本与文档**；大图与训练权重不纳入 Git，需本地按说明准备。

**Remote:** [github.com/kermit0125/Ingredient-Based-Nutritional-Estimation](https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation)

---

## Download & usage / 下载与使用

### 1. Clone and install / 克隆与依赖

```bash
git clone https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation.git
cd Ingredient-Based-Nutritional-Estimation/backend
pip install -r requirements.txt
```

### 2. Download datasets / 下载数据

Two **Roboflow Universe** exports (**YOLOv8** zip), exact folder names and URLs:

- [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md)

Unpack under `backend/data/raw/` so paths match `backend/configs/classes.yaml`.

### 3. Build trainable data / 生成训练数据

From `backend/`:

```bash
python scripts/filter_classes.py
python scripts/split_dataset.py
python scripts/augment.py
```

Optional class-balance report: `python scripts/report_class_balance.py`

Train (example): `yolo detect train model=yolov8m.pt data=data/dataset.yaml`

More detail: [`backend/data/README.md`](backend/data/README.md) (bilingual).

---

## Progress / 当前进度

| Area | Status |
| --- | --- |
| 12-class merge from two Roboflow sources, `classes.yaml` mapping | Done |
| Filter → 80/10/10 split → broccoli/cucumber augmentation → `dataset.yaml` | Done |
| Detection training in-repo scripts (`models/train_detect.py`, etc.) | Planned |
| Segmentation + nutrition modules + FastAPI | Planned |
| Frontend | Teammate / separate repo path TBD |

---

## Repository layout / 目录说明

| Path | Content |
| --- | --- |
| `backend/configs/` | `classes.yaml`, `train_detect.yaml` |
| `backend/scripts/` | Data pipeline Python scripts |
| `backend/data/` | Docs only in git (`README.md`, `DATA_SOURCES.md`); generated data ignored |
| `Documents/` | Workspace notes, API spec, PRD |
