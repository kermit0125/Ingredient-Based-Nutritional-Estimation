# Ingredient-Based Nutritional Estimation

## About / 项目简介

**English:** Course project **INE (Ingredient Nutrition Estimator)** — estimate macros and calories from photos of raw ingredients. **Phase 1** (this milestone) delivers **dataset preprocessing**, **YOLOv8 object detection** training, validation, a **per-100g nutrition CSV**, and a **local HTML dashboard** under `Visualization/`. **Trained weights and `runs/` logs are not in Git** (see `.gitignore`); clone the repo and train locally following the steps below.

**中文：** 课程项目「食材营养识别」：对**烹饪前生鲜食材**做类别检测，并结合营养表输出每 100g 宏量营养（Level 1）。本阶段包含数据管线、YOLOv8 检测训练与评估脚本；**权重与训练产物需本地生成**，按下文「训练方法」操作即可。

**Remote:** [github.com/kermit0125/Ingredient-Based-Nutritional-Estimation](https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation)

**Phase 1 release label:** *Dataset Preprocessing and Implementation of Segmentation Models* — 本仓库在本阶段实际落地的是 **YOLOv8 边界框检测**与数据预处理；**实例分割 / 语义分割模型** 仍属后续规划（见文末 Roadmap）。

---

## Environment / 环境配置

| Item | Recommendation |
|------|----------------|
| **OS** | Windows 10/11 or Linux (examples use Windows paths) |
| **Python** | 3.10+ (tested with 3.13) |
| **GPU** | NVIDIA GPU with CUDA; training script **requires** `torch.cuda.is_available()` |
| **Python env** | `python -m venv .venv` then activate (`.venv\Scripts\activate` on Windows) |

### Install PyTorch (CUDA)

Install **CUDA-enabled PyTorch** first (version aligned with your driver), then project dependencies:

```bash
# Example — check https://pytorch.org/ for the exact command for your CUDA version
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

Verify:

```bash
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

### Install project dependencies

```bash
cd Ingredient-Based-Nutritional-Estimation/backend
pip install -r requirements.txt
```

Core libraries: `ultralytics`, `opencv-python-headless`, `albumentations`, `numpy`, `PyYAML`, etc.

---

## Download datasets / 下载数据

Two **Roboflow Universe** exports (**YOLOv8** zip). Exact names and links:

- [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md)

Unpack under `backend/data/raw/` so paths match [`backend/configs/classes.yaml`](backend/configs/classes.yaml).

---

## Build trainable data / 生成训练数据

From **`backend/`**:

```bash
python scripts/filter_classes.py
python scripts/split_dataset.py
python scripts/augment.py
```

Optional: `python scripts/report_class_balance.py`  
Optional nutrition CSV: `python scripts/build_nutrition_table.py`

More detail: [`backend/data/README.md`](backend/data/README.md).

---

## Training (YOLOv8 detection) / 训练方法

**Working directory must be `backend/`** so dataset paths and run outputs stay consistent.

```bash
cd backend
python models/train_detect.py
```

- **Hyperparameters:** [`backend/configs/train_detect.yaml`](backend/configs/train_detect.yaml) only — edit epochs, batch, device, optimizer, `project`, `name`, etc.; **do not** hardcode these in the script.
- **Dataset entry:** [`backend/data/splits/data.yaml`](backend/data/splits/data.yaml) — Ultralytics reads `train` (both `splits/train` and `augmented/train`), `val`, `test`, `nc`, `names`.

### Where trained models are saved / 训练完成后模型保存在哪里

After training finishes, Ultralytics writes under **`backend/`** (project path is resolved to the backend root in `models/train_detect.py`):

| Path | Description |
|------|-------------|
| **`backend/runs/detect/<run_name>/weights/best.pt`** | **Best checkpoint** (default run name from config: **`exp1`** → `backend/runs/detect/exp1/weights/best.pt`). |
| **`backend/runs/detect/<run_name>/weights/last.pt`** | Last epoch checkpoint. |
| **`backend/runs/detect/<run_name>/`** | Training curves, `results.csv`, `args.yaml`, batch preview images, **`confusion_matrix.png`**, **`BoxPR_curve.png`**, **`BoxP_curve.png`**, **`BoxR_curve.png`**, **`BoxF1_curve.png`**, `results.png`, etc. |

**These files are gitignored** (`runs/`, `*.pt`). They only exist **on your machine** after you train.

---

## Evaluation / 评估

After `best.pt` exists:

```bash
cd backend
python models/evaluate.py
# or: python models/evaluate.py --weights runs/detect/exp1/weights/best.pt
```

Produces metrics on **val**, per-class AP, checks `nutrition_table.csv`, and saves sample predictions under `runs/detect/exp1/eval_viz/` (gitignored).

Running `model.val()` may also create an additional folder such as `runs/detect/val2/` for that validation run.

---

## Demo inference / 单图演示

```bash
cd backend
python models/demo_inference.py --image path/to/image.jpg
```

Uses `best.pt` and `data/nutrition_table.csv` by default.

---

## Visualization dashboard / 结果展示页

Open [`Visualization/index.html`](Visualization/index.html) in a browser. It references charts under `../backend/runs/detect/` (local only). If images do not load with `file://`, serve the repo root:

```bash
# from repository root
python -m http.server 8080
# then open http://localhost:8080/Visualization/
```

---

## Documentation / 文档

| Document | Content |
|----------|---------|
| [`Documents/phase1_analysis_report.md`](Documents/phase1_analysis_report.md) | Phase 1 methodology, metrics summary, limitations |
| [`Documents/workspace_doc.md`](Documents/workspace_doc.md) | Workspace notes |
| [`Documents/api_doc.md`](Documents/api_doc.md) | API spec (evolving) |
| [`backend/data/README.md`](backend/data/README.md) | Data layout & training YAML rules |

---

## Progress / 当前进度

| Area | Status |
|------|--------|
| 10-class merge, `classes.yaml`, filter / split / augment pipeline | Done |
| `train_detect.yaml` + `train_detect.py` + `data/splits/data.yaml` | Done |
| `evaluate.py`, `demo_inference.py`, `build_nutrition_table.py` | Done |
| `Visualization/index.html` report page | Done |
| Segmentation models, portion estimation, FastAPI, frontend | Planned |

---

## Repository layout / 目录说明

| Path | Content |
|------|---------|
| `backend/configs/` | `classes.yaml`, `train_detect.yaml` |
| `backend/models/` | `train_detect.py`, `evaluate.py`, `demo_inference.py` |
| `backend/scripts/` | Data pipeline scripts |
| `backend/data/` | `README.md`, `DATA_SOURCES.md`, tracked YAML stubs; **large image dirs ignored** |
| `Visualization/` | Static HTML dashboard for local metrics / plots |
| `Documents/` | PRD, API notes, **Phase 1 analysis report** |

---

## License / 许可

See repository default; course project — use per instructor requirements.
