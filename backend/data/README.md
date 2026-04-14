# `backend/data` — Data directory / 数据目录

---

## English

This folder holds the full pipeline from **raw download → filter → split → augment → training**. Class definitions and Roboflow name aliases live in `configs/classes.yaml`. **Where to download zips:** see [`DATA_SOURCES.md`](DATA_SOURCES.md).

**Scope note:** **Garlic** and **chilli** are **not** included as detection classes. Typical recipe amounts contribute little to total carbs/protein/fat, so they were dropped from the unified label set and from the nutrition lookup table.

### Layout

| Path | Description |
| --- | --- |
| **`raw/`** | Unpacked **YOLOv8** exports from Roboflow Universe: FOOD-INGREDIENTS (~120 classes), Food ingredient recognition (~38), and optional `Vegetables.v5-danya` instance segmentation. Do not edit; keeps downloads reproducible. |
| **`filtered/`** | Output of `filter_classes.py`: only the **10 project classes**, ids `0–9`, filenames prefixed `ds1_` / `ds2_` / `vegseg_` (per source in `classes.yaml`). Contains `images/`, `labels/`, and a small `data.yaml` (nc/names only). |
| **`splits/`** | Output of `split_dataset.py`: **80/10/10** multilabel stratified **train / val / test**, each with `images/` and `labels/`. Root `data.yaml` points at this tree only (**no** augment folder). |
| **`augmented/train/`** | Output of `augment.py`: **extra** images for **broccoli & cucumber** only (does not replace `splits/train`). |
| **`dataset.yaml`** | **Training index** (root `data/`): same semantics as below. Updated by `split_dataset.py` and `augment.py`. |
| **`splits/data.yaml`** | **Recommended Ultralytics entry** (yaml lives under `splits/`; train lists `../splits/train` + `../augmented/train`). Used by `configs/train_detect.yaml` → `models/train_detect.py`. |
| **`nutrition_table.csv`** | Per-serving nutrition lookup (macros + calories) for supported classes; used with estimated weight in the API layer. Same data as the table below. |

### 10 unified classes (id 0–9)

`bell_pepper`, `tomato`, `onion`, `potato`, `mushroom`, `carrot`, `broccoli`, `cucumber`, `corn`, `egg`

Alias example: **Capsicum** and **bell pepper** → `bell_pepper`.

### `nutrition_table.csv` (same as on disk)

Macros are **per serving** as in the CSV (serving size in the `Quality` column, grams). Values align with the supported classes above (no garlic/chilli rows).

**Raw CSV:**

```csv
Food and Serving,Quality,Calories,Total Fat,Total Carbo-hydrate,Protein
Bell Pepper,148,25,0,6,1
Broccoli,148,45,0.5,8,4
Carrot,78,30,0,7,1
Cucumber,99,10,0,2,1
Mushrooms,84,20,0,3,3
Onion,148,45,0,11,1
Potato,148,110,0,26,3
Sweet Corn,90,90,2.5,18,4
Tomato,148,25,0,5,1
Egg,50,69,4.3,1.3,6.5
```

| Food and Serving | Quality (g) | Calories | Total Fat | Total Carbohydrate | Protein |
| --- | ---:| ---:| ---:| ---:| ---:|
| Bell Pepper | 148 | 25 | 0 | 6 | 1 |
| Broccoli | 148 | 45 | 0.5 | 8 | 4 |
| Carrot | 78 | 30 | 0 | 7 | 1 |
| Cucumber | 99 | 10 | 0 | 2 | 1 |
| Mushrooms | 84 | 20 | 0 | 3 | 3 |
| Onion | 148 | 45 | 0 | 11 | 1 |
| Potato | 148 | 110 | 0 | 26 | 3 |
| Sweet Corn | 90 | 90 | 2.5 | 18 | 4 |
| Tomato | 148 | 25 | 0 | 5 | 1 |
| Egg | 50 | 69 | 4.3 | 1.3 | 6.5 |

### Recommended workflow (from `backend/`)

1. `pip install -r requirements.txt`  
2. `python scripts/filter_classes.py`  
3. `python scripts/split_dataset.py`  
4. (Optional) `python scripts/augment.py`  
5. `python scripts/report_class_balance.py`  
6. Train, e.g. `yolo detect train model=yolov8m.pt data=data/dataset.yaml` or `data=configs/train_detect.yaml`.

**Important:** Use **`data/dataset.yaml`** or **`data/splits/data.yaml`** (both include **two** train roots: `splits/train` + `augmented/train`). Do **not** train on **`augmented/` alone** without `splits/train`, or you drop most labels.

### Instance segmentation refresh (YOLOv8-seg)

After adding or changing sources in `configs/classes.yaml` (e.g. `ds_veg_seg` with polygon labels under `data/raw/`), regenerate everything from `backend/`:

1. `python scripts/filter_classes.py` — unify class ids into `data/filtered/`.  
2. `python scripts/split_dataset.py` — 80/10/10 stratified split → `data/splits/`.  
3. (Optional) `python scripts/augment.py` — extra bbox-based aug for **broccoli/cucumber** only; **polygon label files are skipped** (no bbox warp for masks).  
4. `python scripts/convert_detect_labels_to_seg.py` — copy splits to `data/splits_seg/` (polygons kept; bbox lines become quads). Add `--include-augmented` if you ran step 3.  
5. `python models/train_seg.py` — reads `configs/train_seg.yaml` (default run name `veg_seg_v5`).  
6. Test: `python models/evaluate_seg.py --split val` and `--split test` (mask + box mAP).

### Standalone 3-class segmentation (`veg_seg_3class`)

For **broccoli / cucumber / tomato only**, using **`Vegetables.v5-danya`** polygons — separate from the 10-class merged pipeline:

1. `python scripts/prepare_veg_seg3_dataset.py` — builds `data/veg_seg_3class/`. **Default:** keeps Roboflow’s **train / valid / test** (valid → `val`). Use **`--resplit`** only if you intentionally want a new 80/10/10 from the combined raw pool.  
2. `python scripts/augment_veg_seg3.py` — optional; augments **train only** (writes `aug_train/`). **`val/` and `test/` are never modified** — same files as after step 1.  
3. `python models/train_seg_veg3.py` — weights under `runs/segment_veg3/veg3_seg/`.  
4. `python models/evaluate_seg_veg3.py --split val` and `--split test`.

### Git / large files

`raw/`, `filtered/`, `splits/{train,val,test}/`, `augmented/` are usually **gitignored**; `splits/data.yaml` may be tracked. Keep image blobs locally or on cloud storage; regenerate data on a new machine with the steps above.

---

## 中文

本目录存放食材检测项目从 **原始下载 → 筛选 → 划分 → 增强 → 训练** 的全流程数据。类别与 Roboflow 原始名映射见 `configs/classes.yaml`。**数据 zip 下载地址：** 见 [`DATA_SOURCES.md`](DATA_SOURCES.md)。

**范围说明：** **大蒜（garlic）** 与 **辣椒（chilli）** 不作为检测类别：常见用量对一餐的碳水/蛋白/脂肪总量贡献很小，已从统一标签集与营养对照表中移除。

### 目录结构

| 路径 | 说明 |
| --- | --- |
| **`raw/`** | Roboflow Universe 下载并解压的 **YOLOv8** 数据包：FOOD-INGREDIENTS（约 120 类）、Food ingredient recognition（约 38 类），以及可选的实例分割包 `Vegetables.v5-danya`。**勿改**，便于复现与更新。 |
| **`filtered/`** | `filter_classes.py` 输出：仅 **10 类**，id `0–9`，文件名按数据源为 `ds1_` / `ds2_` / `vegseg_` 等前缀。含 `images/`、`labels/` 及简要 `data.yaml`（仅 nc/names）。 |
| **`splits/`** | `split_dataset.py` 输出：**80/10/10** 多标签分层 **train / val / test**，各含 `images/`、`labels/`。根目录 `data.yaml` 仅描述本树（**不含**增强目录）。 |
| **`augmented/train/`** | `augment.py` 输出：仅对 **西兰花、黄瓜** 的 **额外** 样本（不替换 `splits/train`）。 |
| **`dataset.yaml`** | **训练索引**（位于 `data/` 根）：`train` 为列表，**同时**包含 `splits/train/images` 与 `augmented/train/images`；`val`/`test` 仅来自 `splits`。由 `split_dataset.py` 与 `augment.py` 维护。 |
| **`splits/data.yaml`** | **推荐 Ultralytics 入口**（yaml 在 `splits/` 下）；语义同上。`configs/train_detect.yaml` / `models/train_detect.py` 默认使用该文件。 |
| **`nutrition_table.csv`** | 各类别**每份**热量与三大营养素对照表，供 API 与估重结合使用；与下文表格一致。 |

### 10 个统一类别（id 0–9）

`bell_pepper`, `tomato`, `onion`, `potato`, `mushroom`, `carrot`, `broccoli`, `cucumber`, `corn`, `egg`

别名示例：**Capsicum** 与 **bell pepper** → `bell_pepper`。

### `nutrition_table.csv`（与仓库内文件一致）

以下为 `nutrition_table.csv` 全文（`Quality` 列为该份参考重量，单位 g）。宏量营养素按 CSV 中每份计。

**原始 CSV：**

```csv
Food and Serving,Quality,Calories,Total Fat,Total Carbo-hydrate,Protein
Bell Pepper,148,25,0,6,1
Broccoli,148,45,0.5,8,4
Carrot,78,30,0,7,1
Cucumber,99,10,0,2,1
Mushrooms,84,20,0,3,3
Onion,148,45,0,11,1
Potato,148,110,0,26,3
Sweet Corn,90,90,2.5,18,4
Tomato,148,25,0,5,1
Egg,50,69,4.3,1.3,6.5
```

| Food and Serving | Quality (g) | Calories | Total Fat | Total Carbohydrate | Protein |
| --- | ---:| ---:| ---:| ---:| ---:|
| Bell Pepper | 148 | 25 | 0 | 6 | 1 |
| Broccoli | 148 | 45 | 0.5 | 8 | 4 |
| Carrot | 78 | 30 | 0 | 7 | 1 |
| Cucumber | 99 | 10 | 0 | 2 | 1 |
| Mushrooms | 84 | 20 | 0 | 3 | 3 |
| Onion | 148 | 45 | 0 | 11 | 1 |
| Potato | 148 | 110 | 0 | 26 | 3 |
| Sweet Corn | 90 | 90 | 2.5 | 18 | 4 |
| Tomato | 148 | 25 | 0 | 5 | 1 |
| Egg | 50 | 69 | 4.3 | 1.3 | 6.5 |

### 推荐流程（在 `backend/` 下）

1. `pip install -r requirements.txt`  
2. `python scripts/filter_classes.py`  
3. `python scripts/split_dataset.py`  
4. （可选）`python scripts/augment.py`  
5. `python scripts/report_class_balance.py`  
6. 训练示例：`yolo detect train model=yolov8m.pt data=data/dataset.yaml` 或 `data=configs/train_detect.yaml`。

**注意：** 使用 **`data/dataset.yaml`** 或 **`data/splits/data.yaml`**（二者均为双 `train` 路径）。**不要**只用 `augmented/` 而不含 `splits/train`。

### 实例分割数据刷新（YOLOv8-seg）

在 `configs/classes.yaml` 中增加或修改数据源（例如 `ds_veg_seg` 多边形数据在 `data/raw/`）后，在 `backend/` 下依次执行：

1. `python scripts/filter_classes.py`  
2. `python scripts/split_dataset.py`  
3. （可选）`python scripts/augment.py` — 仅对 **检测框** 标签做西兰花/黄瓜增强；**多边形标签文件会被跳过**（无法用当前脚本对 mask 做几何增强）。  
4. `python scripts/convert_detect_labels_to_seg.py`（若做了增强则加 `--include-augmented`）  
5. `python models/train_seg.py`（默认实验名见 `configs/train_seg.yaml`，如 `veg_seg_v5`）  
6. 测试：`python models/evaluate_seg.py --split val` 与 `--split test`

### 独立三类分割数据（`veg_seg_3class`）

仅 **西兰花 / 黄瓜 / 番茄**，使用 **`Vegetables.v5-danya`** 多边形，与 10 类合并流程无关：

1. `python scripts/prepare_veg_seg3_dataset.py` — 生成 `data/veg_seg_3class/`。**默认**保留 Roboflow 的 **train / valid / test**（valid 写到 `val`）。只有需要**从全集重新 80/10/10** 时才加 `--resplit`。  
2. `python scripts/augment_veg_seg3.py` — 可选；**只增强训练集**（写入 `aug_train/`）。**`val/` 与 `test/` 不会被改动**，与步骤 1 完成后一致。  
3. `python models/train_seg_veg3.py` — 权重在 `runs/segment_veg3/veg3_seg/`。  
4. `python models/evaluate_seg_veg3.py --split val` / `--split test`。

### 仓库与大文件

`raw/`、`filtered/`、`splits/train|val|test/`、`augmented/` 体积大，通常 **`.gitignore`** 排除；`splits/data.yaml` 可纳入版本控制。换机器按上述步骤重新生成图像与标签即可。
