# 食材营养识别系统 · 后端工作区结构

## 目录结构（与仓库同步，2026-03）

> **Git：** 大图与生成数据默认不提交（见仓库根目录 `.gitignore`）。`raw/`、`filtered/`、`splits/`、`augmented/`、`dataset.yaml` 由本地脚本生成；下载地址见 `backend/data/DATA_SOURCES.md`。

```
项目根/
├── README.md                      # 仓库说明（中英）+ 远程地址
├── .gitignore
├── Documents/                     # 产品/接口/工作区文档（本文件等）
│
└── backend/
    ├── README.md                  # 指向根目录与 data 说明
    ├── requirements.txt
    ├── configs/
    │   ├── classes.yaml           # 10 类 + 双数据集 raw 名映射（不含 garlic/chilli）
    │   └── train_detect.yaml      # YOLO 检测数据路径（splits + augmented）
    │
    ├── scripts/                   # 数据准备（当前已实现）
    │   ├── dataset_common.py      # 共用：读 classes、写 dataset.yaml 等
    │   ├── filter_classes.py      # 筛类、合并到 data/filtered/
    │   ├── split_dataset.py       # 80/10/10 多标签划分 → data/splits/
    │   ├── augment.py             # broccoli/cucumber 增强 → data/augmented/train/
    │   └── report_class_balance.py# 训练集类别数量报表
    │
    └── data/                      # 运行时数据目录（大文件不入库）
        ├── README.md              # 数据目录说明（中英双语）
        ├── DATA_SOURCES.md        # Roboflow 下载链接与解压路径约定
        ├── dataset.yaml           # 生成件：双 train 路径（split_dataset / augment 维护）
        ├── raw/                   # 解压后的 Roboflow YOLOv8 包（本地）
        ├── filtered/              # filter_classes 输出（本地）
        ├── splits/                # split_dataset 输出 train/val/test（本地）
        ├── augmented/train/       # augment 输出（本地）
        └── nutrition_table.csv    # （规划中）USDA 营养表

# —— 以下模块为规划/后续实现，目录可能尚未存在 ——
#
# backend/models/   train_detect.py, train_seg.py, evaluate.py, inference.py, weights/*.pt
# backend/nutrition/
# backend/api/
# backend/notebooks/
# backend/tests/    pytest 单元测试（与临时可行性脚本不同）
```

---

## 模块职责说明

### `data/`
存放所有数据文件，按处理阶段分层。`nutrition_table.csv` 是唯一的运行时数据依赖，格式为：

```
class_name, calories, carbs_g, protein_g, fat_g
bell_pepper, 31, 6.0, 1.0, 0.3
tomato, 18, 3.9, 0.9, 0.2
```

### `scripts/`
仅在数据准备阶段运行，不参与推理。执行顺序：

```
filter_classes.py → split_dataset.py → augment.py（可选）→ report_class_balance.py（可选统计）
```

原始数据下载与目录命名见 `backend/data/DATA_SOURCES.md`。

### `models/`
- `train_detect.py` / `train_seg.py`：训练脚本，输出权重至 `weights/`
- `inference.py`：推理入口，被 `api/routes/predict.py` 调用，返回检测/分割结果

### `nutrition/`
纯计算模块，无 IO 依赖，独立可测试。

- `weight_estimator.py`：输入 mask + image_shape + class_name，输出估算克重
- `nutrition_calculator.py`：输入克重 + class_name，查表输出宏量营养素
- `reference_weights.py`：字典常量，格式为 `{class_name: weight_g}`，需根据实验校准

### `api/`
对外暴露三个接口：

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/predict` | POST | 接收图片，返回识别结果 + 营养数据 + 标注图（base64） |
| `/classes` | GET | 返回当前支持的类别列表及参考重量 |
| `/health` | GET | 服务健康检查 |

### `configs/`
- `classes.yaml`：类别列表，`scripts/` 和 `models/` 均依赖此文件，修改类别时只需改这一处
- `train_detect.yaml` / `train_seg.yaml`：指定数据路径、类别数、训练超参数

---

## API 响应结构（`POST /predict`）

```json
{
  "ingredients": [
    {
      "class": "bell_pepper",
      "confidence": 0.92,
      "bbox": [x1, y1, x2, y2],
      "mask_area_ratio": 0.053,
      "estimated_weight_g": 63.6,
      "calories": 20.3,
      "carbs_g": 4.7,
      "protein_g": 0.9,
      "fat_g": 0.2
    }
  ],
  "totals": {
    "calories": 20.3,
    "carbs_g": 4.7,
    "protein_g": 0.9,
    "fat_g": 0.2
  },
  "annotated_image_base64": "<base64 string>"
}
```

---

## 模块依赖关系

```
scripts/          （数据准备，仅离线运行）
    ↓
data/splits/      （训练数据）
    ↓
models/train_*.py （训练，输出 weights/）
    ↓
models/inference.py
    ↑
nutrition/        （被 inference.py 调用）
    ↑
api/routes/predict.py
    ↑
前端（队友负责）
```

---

## 开发阶段划分

| 阶段 | 时间 | 产出 |
| --- | --- | --- |
| Phase 1 · 数据准备 | 3/24–4/1 | `data/splits/` + `nutrition_table.csv` |
| Phase 2a · 检测训练 | 4/1–4/9 | `weights/detect_best.pt`，mAP@0.5 ≥ 0.60 |
| Phase 2b · 分割训练 | 4/10–4/17 | `weights/seg_best.pt` |
| Phase 2c · 营养模块 | 4/10–4/17 | `nutrition/` 三个模块，可独立测试 |
| Phase 3 · API 封装 | 4/5–4/22 | `api/` 完整可运行，`/predict` 联调通过 |
