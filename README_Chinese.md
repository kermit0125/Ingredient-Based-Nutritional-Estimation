# 食材营养估算（INE）

> 英文说明见根目录 [`README.md`](README.md)。

本项目从**生鲜食材**照片中识别食材类别，结合**实例分割或检测框**估算在画面中的占比，再换算为**大致克重**，并依据营养成分表计算**热量、碳水化合物、蛋白质、脂肪**及**全图合计**。适用于备餐、膳食记录等场景下的快速估算（**非**精密秤重）。

仓库：[github.com/kermit0125/Ingredient-Based-Nutritional-Estimation](https://github.com/kermit0125/Ingredient-Based-Nutritional-Estimation)

### 分支 `Instance-Segmentationn`

Git 分支名不能含空格，本仓库使用 **`Instance-Segmentationn`**。该分支包含**独立三类实例分割**流程（西兰花 / 黄瓜 / 番茄）：`prepare_veg_seg3_dataset.py`、`augment_veg_seg3.py`、`train_seg_veg3.py`、`evaluate_seg_veg3.py` 与 `configs/train_seg_veg3.yaml`。大数据与权重（`backend/data/raw/`、`backend/data/veg_seg_3class/`、`runs/`、`*.pt`）已 **gitignore**，克隆后需在本地放入 Roboflow 数据并重新生成与训练。

```bash
git fetch origin
git checkout Instance-Segmentationn
```

---

## 安装

1. **Python** 建议 3.10+；**训练**需要 NVIDIA GPU 与 CUDA。

2. **PyTorch（CUDA）** — 按 [pytorch.org](https://pytorch.org) 与本机驱动选择安装命令，例如：

   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
   ```

3. **项目依赖**（在 `backend` 目录执行）：

   ```bash
   cd Ingredient-Based-Nutritional-Estimation/backend
   pip install -r requirements.txt
   ```

4. **原始数据** — 按 [`backend/data/DATA_SOURCES.md`](backend/data/DATA_SOURCES.md) 下载并解压到 `backend/data/raw/`，路径需与 [`backend/configs/classes.yaml`](backend/configs/classes.yaml) 一致。

---

## 训练

所有命令均在 **`backend/`** 下执行。

### 1. 准备数据

```bash
python scripts/filter_classes.py
python scripts/split_dataset.py
python scripts/augment.py
```

可选：`python scripts/report_class_balance.py`  
可选：`python scripts/build_nutrition_table.py`（生成 `data/nutrition_table.csv`）

### 2. 训练目标检测（YOLOv8）

```bash
python models/train_detect.py
```

超参数见 `configs/train_detect.yaml`。完成后权重一般在 `runs/detect/exp1/weights/best.pt`（若修改 yaml 中的 `project` / `name`，路径会不同）。

### 3. 训练实例分割（YOLOv8-seg）

先将检测标签转为分割训练用多边形标签：

```bash
python scripts/convert_detect_labels_to_seg.py
```

若已做增强并希望分割训练包含增强集：

```bash
python scripts/convert_detect_labels_to_seg.py --include-augmented
```

再训练：

```bash
python models/train_seg.py
```

超参数见 `configs/train_seg.yaml`。完成后权重一般在 `runs/segment/veg_seg_v5/weights/best.pt`（可在 yaml 里改 `name`）。

**仅三类蔬菜的独立分割模型**（西兰花/黄瓜/番茄，多边形数据集）：见 `backend/data/README.md` —— `prepare_veg_seg3_dataset.py` → `augment_veg_seg3.py` → `train_seg_veg3.py` → `evaluate_seg_veg3.py`。

---

## 测试与使用

### 检测模型指标与可视化

```bash
python models/evaluate.py --weights runs/detect/exp1/weights/best.pt
```

### 单图：检测 + 每 100g 营养（画框）

```bash
python models/demo_inference.py --image path/to/image.jpg --weights runs/detect/exp1/weights/best.pt
```

### 单图：估重 + 实例与全图营养（推荐分割权重）

```bash
python models/inference.py --image path/to/image.jpg --weights runs/segment/veg_seg_v5/weights/best.pt
```

暂无分割权重时，可临时指定**检测**权重（以框面积近似，精度弱于掩码）：

```bash
python models/inference.py --image path/to/image.jpg --weights runs/detect/exp1/weights/best.pt
```

### 分割模型验证（需已存在分割权重）

```bash
python models/evaluate_seg.py --weights runs/segment/veg_seg_v5/weights/best.pt --data data/splits_seg/data.yaml --split test
```

### HTTP 服务

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- `GET /health`：健康检查  
- `GET /classes`：类别与参考克重  
- `POST /predict`：表单字段 `image` 上传 JPG/PNG  

可选环境变量：`INE_SEG_WEIGHTS`（`.pt` 路径）、`INE_CONF`（置信度阈值，默认 `0.5`）。

### 估重标定

编辑 `backend/nutrition/reference_weights.py` 中各类别的参考克重；精度限制与改进思路见下文「重量估算精度」。

---

## 模型结果与分析

### 检测模型（YOLOv8m）

下表摘自 [`Documents/phase1_analysis_report.md`](Documents/phase1_analysis_report.md) 中**一次代表性验证集运行**（命令：`python models/evaluate.py`）。**随机种子与训练轮次变化后数值会浮动**，请以本机 `evaluate.py` 输出及 `runs/detect/.../results.csv` 为准。

| 指标（验证集） | 示例数值 |
|----------------|----------|
| mAP@0.5 | 约 0.954 |
| 平均精确率（Precision） | 约 0.957 |
| 平均召回率（Recall） | 约 0.901 |
| 与常见目标 mAP@0.5 ≥ 0.60 | 达标 |

**逐类（同一次运行）：** 多数类别 AP@0.5 较高；该快照中 **cucumber（黄瓜）** 相对较低（约 0.76），仍高于评估脚本中常用的 0.50 预警线。若某类持续偏低，可增加样本或增强，并对照 `report_class_balance.py`。

### 分割模型

掩码 mAP、训练曲线等位于本机 `runs/segment/...`（默认不入库）。训练结束后执行：

```bash
python models/evaluate_seg.py --weights runs/segment/veg_seg_v5/weights/best.pt --data data/splits_seg/data.yaml --split test
```

请自行记录终端与 `runs/segment/...` 中的指标；仓库**不固定存档**每一次分割实验数字。

### 小结

- **检测**：双源合并、分层划分与针对性增强后，验证集整体指标较好；少数类仍有提升空间。  
- **估重与营养**：由「掩码或框面积 / 全图面积 × 参考克重」与营养表推算，与检测 mAP **不是同一套精度概念**；即使检测很准，克重仍可能偏差较大（见下一节）。

---

## 重量估算精度

当前输出的**克重仅为估算**，精度有限，请作为**参考级**使用，不可替代秤。主要原因：

1. **缺乏大规模「图像 ↔ 真实克重」配对数据** — `nutrition/reference_weights.py` 中为按类设定的参考值，属**启发式初值**，**未**针对你的相机高度、焦距、台面与光照单独标定。  
2. **几何假设偏理想** — 默认食材落在**同一平面**，且可见面积与可食质量近似成比例；大角度、堆叠、遮挡会使面积比失真。  
3. **分割监督来源** — 若多边形由**检测框**生成，掩码弱于真实实例分割，**面积比易有系统偏差**。  
4. **营养表为静态每 100g 值** — 未区分品种、成熟度、含水率等，误差会叠加在估重误差上。

### 可考虑的改进方向

| 方向 | 说明 |
|------|------|
| **场景与参考克重标定** | 固定拍摄姿势下，用若干已知真重样本拟合每类或全局缩放因子，迭代更新 `reference_weights.py`。 |
| **画面内参考物** | 放置已知尺寸标定物，估计像素到实际长度比例，再结合厚度/体积假设。 |
| **深度 / 立体视觉** | 深度相机、双目或单目深度 + 粗略体积模型，替代纯平面面积比。 |
| **高质量分割标注** | 使用真实多边形/掩码训练，减少「框即掩码」误差。 |
| **学习式份量回归** | 在检测/分割骨干上增加份量头，用弱/强质量或体积标注训练。 |
| **交互校准** | 允许用户输入总重或乘性修正，用反馈微调参考克重或每用户配置。 |

---

## 目录概要

| 路径 | 说明 |
|------|------|
| `backend/configs/` | 类别与训练配置 |
| `backend/data/` | 数据与营养表（大图多为本地生成） |
| `backend/models/` | 训练、评估、推理脚本 |
| `backend/nutrition/` | 参考克重与营养计算 |
| `backend/scripts/` | 数据与标签处理 |
| `backend/api/` | FastAPI 入口 |
| `Visualization/` | 本地训练曲线等静态页 |

更多说明见 `Documents/` 与 `backend/data/README.md`。
