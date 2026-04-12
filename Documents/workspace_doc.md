# 食材营养识别系统 · 后端工作区说明

**同步说明：** 与仓库当前代码一致（2026-04）。大图、`runs/`、权重及本地数据目录默认不入库，见根目录 `.gitignore`。数据下载路径见 `backend/data/DATA_SOURCES.md`。

---

## 目录结构（项目根 → backend）

```
项目根/
├── README.md                 # 安装、训练、测试、模型结果与估重说明（主文档）
├── .gitignore
├── Documents/                # PRD、接口、工作区、阶段报告等
├── Visualization/          # 本地训练曲线等静态页（依赖本机 runs/）
│
└── backend/
    ├── README.md             # 可指向根目录 README 或 data 说明
    ├── requirements.txt
    │
    ├── configs/
    │   ├── classes.yaml      # nc、canonical 类别名、双数据集 raw→canonical 映射
    │   ├── train_detect.yaml # YOLOv8 检测训练超参
    │   └── train_seg.yaml    # YOLOv8-seg 训练超参
    │
    ├── scripts/
    │   ├── dataset_common.py
    │   ├── filter_classes.py
    │   ├── split_dataset.py
    │   ├── augment.py
    │   ├── report_class_balance.py
    │   ├── build_nutrition_table.py
    │   └── convert_detect_labels_to_seg.py   # 检测标签 → 多边形标签，供分割训练
    │
    ├── models/
    │   ├── train_detect.py
    │   ├── train_seg.py
    │   ├── evaluate.py
    │   ├── demo_inference.py    # 检测 + 每 100g 营养画框
    │   └── inference.py         # 分割/检测权重 + 估重 + 营养 + base64 图
    │
    ├── nutrition/
    │   ├── reference_weights.py
    │   ├── weight_estimator.py
    │   └── nutrition_calculator.py
    │
    ├── api/
    │   └── main.py             # FastAPI：/health、/classes、/predict
    │
    └── data/                   # 本地生成为主（多数被 ignore）
        ├── README.md
        ├── DATA_SOURCES.md
        ├── dataset.yaml        # split_dataset / augment 维护
        ├── nutrition_table.csv
        ├── raw/
        ├── filtered/
        ├── splits/
        ├── splits_seg/         # convert_detect_labels_to_seg 输出
        ├── augmented/
        └── augmented_seg/      # 可选，与 --include-augmented 对应
```

训练产物路径示例（以默认 yaml 为准）：`backend/runs/detect/exp1/weights/best.pt`、`backend/runs/segment/exp1/weights/best.pt`。

---

## 模块职责

### `data/`

按阶段存放原始与处理后数据。运行时推理依赖 `nutrition_table.csv`（可由 `build_nutrition_table.py` 生成）。表头示例：

`canonical_name, calories_kcal, carbohydrate_g, protein_g, fat_g, usda_fdc_hint`

### `scripts/`

离线数据管线，不参与在线推理。常见顺序：

`filter_classes.py` → `split_dataset.py` → `augment.py`（可选）→ `report_class_balance.py`（可选）  
分割前：`convert_detect_labels_to_seg.py`（在已有 `data/splits/` 时）。

### `models/`

- `train_detect.py` / `train_seg.py`：读取对应 yaml，输出至 `runs/.../weights/best.pt`。  
- `evaluate.py`：检测模型验证集指标、营养表覆盖检查、测试集抽样可视化。  
- `demo_inference.py`：单图检测 + 营养表每 100 g 信息叠加。  
- `inference.py`：`run_predict()`，供 CLI 与 API 调用。

### `nutrition/`

纯计算：`reference_weights.py`（参考克重）、`weight_estimator.py`（面积比→克重）、`nutrition_calculator.py`（克重→宏量与热量）。

### `api/`

`main.py` 内挂载 FastAPI 应用：详见 `Documents/api_doc.md`（与实现一致的版本）。
同时提供 `/` 前端演示页与 `/static/` 静态资源，用于完整联调展示上传、标注图、营养表和宏量图表。

### `configs/`

`classes.yaml` 为类别单一事实来源；训练 yaml 仅写超参与 `data` 路径，不在脚本中硬编码。

---

## `POST /predict` 响应结构（与 `inference.run_predict` 一致）

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
      "fat_g": 0.2,
      "estimate_note": "可选，如估重截断或营养缺失提示"
    }
  ],
  "totals": {
    "calories": 20.3,
    "carbs_g": 4.7,
    "protein_g": 0.9,
    "fat_g": 0.2
  },
  "annotated_image_base64": "<JPEG base64>",
  "message": null
}
```

无有效实例时：`ingredients` 为空，`totals` 全 0，`message` 可为提示字符串，`annotated_image_base64` 为原图 JPEG 编码。

---

## 依赖关系（数据流）

```
scripts/  →  data/splits/（及 splits_seg、augmented*）
                ↓
        models/train_detect.py | train_seg.py  →  runs/*/weights/best.pt
                ↓
        models/inference.py  ←  nutrition/
                ↑
        api/main.py
```

前端或其他客户端通过 HTTP 调用 `api/main.py`；命令行可直接运行 `models/inference.py`。

---

## 阶段与仓库状态（摘要）

| 内容 | 状态 |
|------|------|
| 数据合并、划分、增强脚本 | 已有 |
| 检测训练与评估 | 已有 |
| 分割标签转换与分割训练入口 | 已有 |
| `nutrition/` 与 `inference.py` | 已有 |
| FastAPI `api/main.py` | 已有 |

具体指标与估重局限见根目录 `README.md` 与 `Documents/phase1_analysis_report.md`。
