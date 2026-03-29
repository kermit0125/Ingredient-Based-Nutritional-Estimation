# Raw data sources / 原始数据来源

## English

This project expects **two Roboflow Universe** exports in **YOLOv8** format. Download the zip(s), extract them, and place the folders under `backend/data/raw/` using the **exact folder names** referenced in `configs/classes.yaml`:

| Key in `classes.yaml` | Expected path under `backend/data/raw/` | Roboflow Universe |
| --- | --- | --- |
| `ds1` | `FOOD-INGREDIENTS dataset.v4i.yolov8` | [food-ingredients-dataset / v4](https://universe.roboflow.com/food-recipe-ingredient-images-0gnku/food-ingredients-dataset/dataset/4) |
| `ds2` | `Food ingredient recognition.v4i.yolov8` | [food-ingredient-recognition / v4](https://universe.roboflow.com/thanh-huy-phan/food-ingredient-recognition/dataset/4) |

Steps on Roboflow: open the dataset → **Download** → choose **YOLOv8** → unzip so each export contains `data.yaml`, `train/`, `valid/`, `test/`.

Then from `backend/`:

```bash
pip install -r requirements.txt
python scripts/filter_classes.py
python scripts/split_dataset.py
python scripts/augment.py   # optional
```

Licenses and attribution follow each Roboflow dataset page (e.g. CC BY 4.0 as shown on those versions).

---

## 中文

本项目需要两个 **Roboflow Universe** 的 **YOLOv8** 格式数据集。下载 zip 并解压到 `backend/data/raw/`，**目录名**须与 `configs/classes.yaml` 中 `path` 一致：

| 配置中的数据源 | `backend/data/raw/` 下文件夹名 | Roboflow 链接 |
| --- | --- | --- |
| `ds1` | `FOOD-INGREDIENTS dataset.v4i.yolov8` | [food-ingredients-dataset 第 4 版](https://universe.roboflow.com/food-recipe-ingredient-images-0gnku/food-ingredients-dataset/dataset/4) |
| `ds2` | `Food ingredient recognition.v4i.yolov8` | [food-ingredient-recognition 第 4 版](https://universe.roboflow.com/thanh-huy-phan/food-ingredient-recognition/dataset/4) |

在 Roboflow 上：**Download** → 选择 **YOLOv8** → 解压后应包含 `data.yaml`、`train/`、`valid/`、`test/`。

然后在 `backend/` 下执行 `filter_classes.py` → `split_dataset.py` →（可选）`augment.py`。具体见 `README.md`。

许可证与署名以各 Roboflow 数据集页面为准。
