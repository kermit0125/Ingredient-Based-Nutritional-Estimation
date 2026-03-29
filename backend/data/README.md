# `backend/data` — Data directory / 数据目录

---

## English

This folder holds the full pipeline from **raw download → filter → split → augment → training**. Class definitions and Roboflow name aliases live in `configs/classes.yaml`. **Where to download zips:** see [`DATA_SOURCES.md`](DATA_SOURCES.md).

### Layout

| Path | Description |
| --- | --- |
| **`raw/`** | Unpacked **YOLOv8** exports from Roboflow Universe. Two sources: FOOD-INGREDIENTS (~120 classes) and Food ingredient recognition (~38). Do not edit; keeps downloads reproducible. |
| **`filtered/`** | Output of `filter_classes.py`: only the **12 project classes**, ids `0–11`, filenames prefixed `ds1_` / `ds2_`. Contains `images/`, `labels/`, and a small `data.yaml` (nc/names only). |
| **`splits/`** | Output of `split_dataset.py`: **80/10/10** multilabel stratified **train / val / test**, each with `images/` and `labels/`. Root `data.yaml` points at this tree only (**no** augment folder). |
| **`augmented/train/`** | Output of `augment.py`: **extra** images for **broccoli & cucumber** only (does not replace `splits/train`). |
| **`dataset.yaml`** | **Main training file**: `train` is a **list** with `splits/train/images` **and** `augmented/train/images`; `val` / `test` come from `splits` only. Updated by `split_dataset.py` and `augment.py`. |
| **`nutrition_table.csv`** | (Planned) per-100g nutrition lookup for the API; separate from detection data. |

### 12 unified classes (id 0–11)

`bell_pepper`, `tomato`, `onion`, `potato`, `mushroom`, `carrot`, `broccoli`, `cucumber`, `corn`, `egg`, `garlic`, `chilli`

Alias examples: **Capsicum** and **bell pepper** → `bell_pepper`; **Chili Pepper -Khursani-** and **chilli** → `chilli`.

### Recommended workflow (from `backend/`)

1. `pip install -r requirements.txt`  
2. `python scripts/filter_classes.py`  
3. `python scripts/split_dataset.py`  
4. (Optional) `python scripts/augment.py`  
5. `python scripts/report_class_balance.py`  
6. Train, e.g. `yolo detect train model=yolov8m.pt data=data/dataset.yaml` or `data=configs/train_detect.yaml`.

**Important:** Point training at **`data/dataset.yaml`** (or equivalent). Using only `splits/data.yaml` or only `augmented/` drops half of the train data.

### Git / large files

`raw/`, `filtered/`, `splits/`, `augmented/` are usually **gitignored**; keep them locally or on cloud storage. Commit `configs/classes.yaml`, scripts, and this README; regenerate data on a new machine with the steps above.

---

## 中文

本目录存放食材检测项目从 **原始下载 → 筛选 → 划分 → 增强 → 训练** 的全流程数据。类别与 Roboflow 原始名映射见 `configs/classes.yaml`。**数据 zip 下载地址：** 见 [`DATA_SOURCES.md`](DATA_SOURCES.md)。

### 目录结构

| 路径 | 说明 |
| --- | --- |
| **`raw/`** | Roboflow Universe 下载并解压的 **YOLOv8** 数据包。当前两个来源：FOOD-INGREDIENTS（约 120 类）、Food ingredient recognition（约 38 类）。**勿改**，便于复现与更新。 |
| **`filtered/`** | `filter_classes.py` 输出：仅 **12 类**，id `0–11`，文件名 `ds1_` / `ds2_` 前缀。含 `images/`、`labels/` 及简要 `data.yaml`（仅 nc/names）。 |
| **`splits/`** | `split_dataset.py` 输出：**80/10/10** 多标签分层 **train / val / test**，各含 `images/`、`labels/`。根目录 `data.yaml` 仅描述本树（**不含**增强目录）。 |
| **`augmented/train/`** | `augment.py` 输出：仅对 **西兰花、黄瓜** 的 **额外** 样本（不替换 `splits/train`）。 |
| **`dataset.yaml`** | **训练主入口**：`train` 为列表，**同时**包含 `splits/train/images` 与 `augmented/train/images`；`val`/`test` 仅来自 `splits`。由 `split_dataset.py` 与 `augment.py` 维护。 |
| **`nutrition_table.csv`** | （计划中）每 100g 营养表，供 API；与检测数据独立。 |

### 12 个统一类别（id 0–11）

`bell_pepper`, `tomato`, `onion`, `potato`, `mushroom`, `carrot`, `broccoli`, `cucumber`, `corn`, `egg`, `garlic`, `chilli`

别名示例：**Capsicum** 与 **bell pepper** → `bell_pepper`；**Chili Pepper -Khursani-** 与 **chilli** → `chilli`。

### 推荐流程（在 `backend/` 下）

1. `pip install -r requirements.txt`  
2. `python scripts/filter_classes.py`  
3. `python scripts/split_dataset.py`  
4. （可选）`python scripts/augment.py`  
5. `python scripts/report_class_balance.py`  
6. 训练示例：`yolo detect train model=yolov8m.pt data=data/dataset.yaml` 或 `data=configs/train_detect.yaml`。

**注意：** 必须使用 **`data/dataset.yaml`**（或等价双 `train` 配置）。只用 `splits/data.yaml` 或只用 `augmented/` 会漏掉另一半训练数据。

### 仓库与大文件

`raw/`、`filtered/`、`splits/`、`augmented/` 体积大，通常 **`.gitignore`** 排除。提交代码保留 **`configs/classes.yaml`**、**脚本**与本 **README**；换机器按上述步骤重新生成数据即可。
