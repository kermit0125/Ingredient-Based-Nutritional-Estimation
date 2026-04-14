# Ingredient Nutrition Estimation (INE)

[简体中文说明](README_Chinese.md)

This project identifies **raw ingredient** categories from photos, estimates each instance’s **share of the image** using **instance segmentation or detection boxes**, converts that to an **approximate mass in grams**, and computes **calories, carbohydrates, protein, and fat** from a nutrition table—including **per-image totals**. It is meant for quick meal-prep or food-logging style estimates, **not** precision scale measurements.

Repository: [github.com/kermit0125/Ingredient-Based-Nutritional-Estimation](https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation)

### Branch `Instance-Segmentationn`

Git branch names cannot contain spaces; this branch uses **`Instance-Segmentationn`**. It carries the **standalone 3-class instance segmentation** workflow (broccoli, cucumber, tomato): `scripts/prepare_veg_seg3_dataset.py`, `scripts/augment_veg_seg3.py`, `models/train_seg_veg3.py`, `models/evaluate_seg_veg3.py`, and `configs/train_seg_veg3.yaml`. Large blobs (`backend/data/raw/`, `backend/data/veg_seg_3class/`, `runs/`, `*.pt`) are **gitignored**; clone this branch, add the Roboflow zip locally, then regenerate data and train.

```bash
git fetch origin
git checkout Instance-Segmentationn
```

---

## Installation

1. **Python** 3.10+ recommended. **Training** requires an NVIDIA GPU with CUDA.

2. **PyTorch (CUDA)** — follow [pytorch.org](https://pytorch.org) for a command that matches your driver, for example:

   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
   ```

3. **Project dependencies** (from the `backend` directory):

   ```bash
   cd Ingredient-Based-Nutritional-Estimation/backend
   pip install -r requirements.txt
   ```

4. **Raw data** — download and unpack per [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md) under `backend/data/raw/` so paths match [`backend/configs/classes.yaml`](backend/configs/classes.yaml).

---

## Training

Run all commands from **`backend/`**.

### 1. Prepare data

```bash
python scripts/filter_classes.py
python scripts/split_dataset.py
python scripts/augment.py
```

Optional: `python scripts/report_class_balance.py`  
Optional: `python scripts/build_nutrition_table.py` (writes `data/nutrition_table.csv`)

### 2. Train object detection (YOLOv8)

```bash
python models/train_detect.py
```

Hyperparameters: `configs/train_detect.yaml`. Weights usually land at `runs/detect/exp1/weights/best.pt` (paths change if you edit `project` / `name` in the yaml).

### 3. Train instance segmentation (YOLOv8-seg)

Convert detection labels to polygon labels for segmentation training:

```bash
python scripts/convert_detect_labels_to_seg.py
```

If you use augmentation and want the segmentation train set to include it:

```bash
python scripts/convert_detect_labels_to_seg.py --include-augmented
```

Then train:

```bash
python models/train_seg.py
```

Hyperparameters: `configs/train_seg.yaml`. Weights usually land at `runs/segment/<name>/weights/best.pt` (default run name `veg_seg_v5`; change `name` in the yaml to avoid overwriting).

**Standalone 3-class veg segmentation** (broccoli/cucumber/tomato only, polygon dataset): see [`backend/data/README.md`](backend/data/README.md) — `prepare_veg_seg3_dataset.py` → `augment_veg_seg3.py` → `train_seg_veg3.py` → `evaluate_seg_veg3.py`.

---

## Testing and usage

### Detection metrics and visualizations

```bash
python models/evaluate.py --weights runs/detect/exp1/weights/best.pt
```

### Single image: detection + per-100g nutrition (boxes)

```bash
python models/demo_inference.py --image path/to/image.jpg --weights runs/detect/exp1/weights/best.pt
```

### Single image: mass estimate + per-instance and full-image macros (segmentation weights recommended)

```bash
python models/inference.py --image path/to/image.jpg --weights runs/segment/veg_seg_v5/weights/best.pt
```

If segmentation weights are not ready yet, you can temporarily point to **detection** weights (box area as a proxy; weaker than masks):

```bash
python models/inference.py --image path/to/image.jpg --weights runs/detect/exp1/weights/best.pt
```

### Validate the segmentation model (requires trained segmentation weights)

```bash
python models/evaluate_seg.py --weights runs/segment/veg_seg_v5/weights/best.pt --data data/splits_seg/data.yaml --split test
```

Equivalent: `yolo segment val model=runs/segment/veg_seg_v5/weights/best.pt data=data/splits_seg/data.yaml split=test`

### HTTP service

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- `GET /health` — health check  
- `GET /classes` — class list and reference gram weights  
- `POST /predict` — multipart form field `image` (JPG/PNG)  

Optional environment variables: `INE_SEG_WEIGHTS` (path to `.pt`), `INE_CONF` (score threshold, default `0.5`).

### Calibrating mass estimates

Edit per-class reference grams in `backend/nutrition/reference_weights.py`. For limitations and improvement ideas, see **Mass estimation accuracy** below.

---

## Model results and analysis

### Detection model (YOLOv8m)

The table below summarizes **one representative validation run** recorded in [`Documents/phase1_analysis_report.md`](Documents/phase1_analysis_report.md) (command: `python models/evaluate.py`). **Numbers shift with random seed and training**—treat your local `evaluate.py` output and `runs/detect/.../results.csv` as authoritative.

| Metric (val) | Example value |
|--------------|----------------|
| mAP@0.5 | ~0.954 |
| Mean precision | ~0.957 |
| Mean recall | ~0.901 |
| vs. common target mAP@0.5 ≥ 0.60 | Pass |

**Per-class (same run):** Most classes show high AP@0.5; in this snapshot **cucumber** is relatively lower (~0.76) but still above the usual 0.50 warning line in the eval script. If a class stays low, add data or augmentation and cross-check with `report_class_balance.py`.

### Segmentation model

Mask mAP and training curves live under local `runs/segment/...` (not committed by default). After training, run `python models/evaluate_seg.py` (val/test) or `yolo segment val` as in the section above, and keep your own notes; the repo does **not** pin every segmentation experiment’s numbers.

### Takeaways

- **Detection:** After merging Roboflow sources (per `classes.yaml`), stratified splits, and targeted augmentation, overall val metrics are strong; tail classes can still improve.  
- **Mass and nutrition:** Derived from `(mask or box area / full image) × reference grams` plus the nutrition table—**not the same notion of accuracy as detection mAP**; masses can be far off even when boxes are good (see next section).

---

## Mass estimation accuracy

Reported **grams are estimates only**; accuracy is limited. Treat outputs as **reference-level**, not a substitute for a scale. Main reasons:

1. **No large image↔ground-truth mass dataset** — `nutrition/reference_weights.py` uses per-class reference masses as **heuristic defaults**, **not** calibrated to your camera height, focal length, tabletop, or lighting.  
2. **Idealized geometry** — the formula assumes ingredients lie on a **common plane** and that visible area scales with edible mass; tilt, stacking, and occlusion break that.  
3. **Segmentation supervision** — if polygons come from **boxes**, masks are weaker than true instance masks and **area ratios can be biased**.  
4. **Static nutrition table** — per-100g values ignore cultivar, ripeness, water content, etc.; error stacks on top of mass error.

### Possible improvements

| Direction | Idea |
|-----------|------|
| **Scene / reference-mass calibration** | Under a fixed camera pose, fit per-class scale factors (or a global scale) from a few weighed samples; iterate `reference_weights.py`. |
| **In-frame reference objects** | Use a known-size target to map pixels to real length, then add simple thickness/volume assumptions. |
| **Depth / stereo** | RGB-D, binocular, or monocular depth plus a coarse volume model instead of flat area ratio. |
| **Better mask labels** | Train on real polygon/mask annotations to reduce box-as-mask error. |
| **Learned portion regression** | Weak/strong mass or volume labels on a head over the detector/segmenter backbone. |
| **Interactive calibration** | Let users enter total mass or a multiplier; tune references or per-user settings from feedback. |

---

## Repository layout

| Path | Role |
|------|------|
| `backend/configs/` | Classes and training configs |
| `backend/data/` | Data and nutrition CSV (large blobs usually local-only) |
| `backend/models/` | Train, evaluate, and inference scripts |
| `backend/nutrition/` | Reference masses and macro math |
| `backend/scripts/` | Data and label pipelines |
| `backend/api/` | FastAPI entrypoint |
| `Visualization/` | Static dashboard for local training plots |

See also `Documents/` and `backend/data/README.md`.
