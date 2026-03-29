# API 接口设计文档 · 食材营养识别系统

**版本**：V1.1.0
**最后更新**：2026/03/28
**后端负责人**：Keming
**前端负责人**：Zhaozhe
**Base URL（本地开发）**：`http://localhost:8000`
**Base URL（部署后）**：待定

> 本文档为前后端接口约定，字段名、类型、结构一经双方确认不得单方面修改。如需变更请在 Teams 中同步后更新本文档版本号。

---

## 目录

1. [通用约定](#1-通用约定)
2. [GET /health](#2-get-health)
3. [GET /classes](#3-get-classes)
4. [POST /predict](#4-post-predict)
5. [错误响应结构](#5-错误响应结构)
6. [前端对接说明](#6-前端对接说明)
7. [变更记录](#7-变更记录)

---

## 1. 通用约定

### 请求格式

- 图片上传使用 `multipart/form-data`
- 其余请求（如有）使用 `application/json`

### 响应格式

所有接口统一返回 JSON，结构如下：

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| code | int | 业务状态码，200 表示成功，详见第 5 节 |
| message | string | 状态描述，成功时为 `"success"` |
| data | object / null | 业务数据，失败时为 `null` |

### 图片限制

| 项目 | 限制 |
| --- | --- |
| 支持格式 | JPG、PNG |
| 最大文件大小 | 10 MB |
| 最小分辨率 | 300 × 300 px |
| 推荐拍摄方式 | 食材平铺于桌面/切菜板，俯拍或斜 45° 拍摄 |

### 单位约定

| 字段类型 | 单位 |
| --- | --- |
| 重量 | 克（g） |
| 热量 | 千卡（kcal） |
| 碳水 / 蛋白质 / 脂肪 | 克（g） |
| 置信度 | 浮点数，范围 0–1 |
| 坐标 | 像素，基于原始输入图片尺寸 |
| 面积比 | 浮点数，范围 0–1 |

---

## 2. GET /health

### 描述

服务健康检查，用于确认后端是否正常运行。前端可在页面初始化时调用，判断服务可用性。

### 请求

无参数。

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "status": "ok",
    "model_loaded": true,
    "supported_classes_count": 12
  }
}
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| status | string | Service status, `"ok"` when running normally |
| model_loaded | bool | Whether model weights are loaded |
| supported_classes_count | int | Number of supported ingredient classes |

---

## 3. GET /classes

### 描述

返回当前系统支持的全部食材类别列表，包含类别名（英文/中文）及对应的参考基准重量。前端可用于展示支持范围提示。

### 请求

无参数。

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "classes": [
      {
        "class_id": 0,
        "class_name": "bell_pepper",
        "display_name": "Bell Pepper",
        "reference_weight_g": 120
      },
      {
        "class_id": 1,
        "class_name": "tomato",
        "display_name": "Tomato",
        "reference_weight_g": 150
      },
      {
        "class_id": 2,
        "class_name": "carrot",
        "display_name": "Carrot",
        "reference_weight_g": 200
      }
    ]
  }
}
```

### 响应字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| classes | array | 类别列表 |
| classes[].class_id | int | 类别 ID，与模型输出一致 |
| classes[].class_name | string | 类别英文名（snake_case） |
| classes[].display_name | string | 前端展示用中文名 |
| classes[].reference_weight_g | float | 该类别参考基准重量（g） |

---

## 4. POST /predict

### 描述

核心推理接口。接收一张食材图片，返回识别结果、估算重量、宏量营养素及带标注的结果图像。

### 请求

**Content-Type**：`multipart/form-data`

| 参数名 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| image | file | 是 | 图片文件，JPG 或 PNG |

### 响应示例

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "ingredients": [
      {
        "instance_id": 0,
        "class_name": "bell_pepper",
        "display_name": "Bell Pepper",
        "confidence": 0.92,
        "bbox": [45, 80, 210, 290],
        "mask_area_ratio": 0.053,
        "estimated_weight_g": 63.6,
        "calories": 19.7,
        "carbs_g": 3.8,
        "protein_g": 0.6,
        "fat_g": 0.2
      },
      {
        "instance_id": 1,
        "class_name": "tomato",
        "display_name": "Tomato",
        "confidence": 0.88,
        "bbox": [300, 120, 480, 330],
        "mask_area_ratio": 0.071,
        "estimated_weight_g": 106.5,
        "calories": 19.2,
        "carbs_g": 4.1,
        "protein_g": 1.0,
        "fat_g": 0.2
      }
    ],
    "totals": {
      "calories": 38.9,
      "carbs_g": 7.9,
      "protein_g": 1.6,
      "fat_g": 0.4
    },
    "image_info": {
      "original_width": 640,
      "original_height": 480,
      "detected_count": 2
    },
    "annotated_image_base64": "<base64 encoded PNG string>"
  }
}
```

### 响应字段详细说明

**`ingredients[]`** — 每个检测到的食材实例

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| instance_id | int | 实例编号，从 0 开始，同一张图内唯一 |
| class_name | string | 类别英文名（snake_case） |
| display_name | string | 前端展示用中文名 |
| confidence | float | 置信度，0–1，已过滤 < 0.5 的结果 |
| bbox | int[4] | 边界框 `[x1, y1, x2, y2]`，左上角和右下角像素坐标 |
| mask_area_ratio | float | 掩码像素面积 / 全图像素面积，即 ri |
| estimated_weight_g | float | 估算重量（g），保留 1 位小数 |
| calories | float | 该实例热量（kcal），保留 1 位小数 |
| carbs_g | float | 碳水化合物（g），保留 1 位小数 |
| protein_g | float | 蛋白质（g），保留 1 位小数 |
| fat_g | float | 脂肪（g），保留 1 位小数 |

**`totals`** — 全图所有实例营养汇总

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| calories | float | 总热量（kcal） |
| carbs_g | float | 总碳水（g） |
| protein_g | float | 总蛋白质（g） |
| fat_g | float | 总脂肪（g） |

**`image_info`** — 图片元信息

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| original_width | int | 输入图片原始宽度（px） |
| original_height | int | 输入图片原始高度（px） |
| detected_count | int | 检测到的食材实例总数 |

**`annotated_image_base64`**

- 类型：string
- 带分割掩码和类别标签的结果图，PNG 格式，Base64 编码
- 前端解码方式：`<img src="data:image/png;base64,{annotated_image_base64}" />`
- 尺寸与输入图片一致（不缩放）

### 无食材检出时的响应

当图片中未检测到任何支持类别的食材时，返回如下结构（`code` 仍为 200，`ingredients` 为空数组）：

```json
{
  "code": 200,
  "message": "no ingredients detected",
  "data": {
    "ingredients": [],
    "totals": {
      "calories": 0,
      "carbs_g": 0,
      "protein_g": 0,
      "fat_g": 0
    },
    "image_info": {
      "original_width": 640,
      "original_height": 480,
      "detected_count": 0
    },
    "annotated_image_base64": "<原图 base64，无标注>"
  }
}
```

---

## 5. 错误响应结构

所有错误均返回统一结构，HTTP 状态码与 `code` 字段同步。

```json
{
  "code": 400,
  "message": "unsupported image format, only JPG and PNG are accepted",
  "data": null
}
```

### 错误码一览

| HTTP 状态码 | code | message | 说明 |
| --- | --- | --- | --- |
| 400 | 400 | `unsupported image format` | 图片格式不支持 |
| 400 | 400 | `image too large` | 图片超过 10MB |
| 400 | 400 | `image resolution too low` | 分辨率低于 300×300 |
| 422 | 422 | `missing required field: image` | 请求体缺少 image 字段 |
| 500 | 500 | `model inference failed` | 模型推理异常 |
| 503 | 503 | `model not loaded` | 模型权重未加载，服务未就绪 |

---

## 6. 前端对接说明

### 上传图片示例（JavaScript）

```javascript
async function predict(file) {
  const formData = new FormData();
  formData.append("image", file);

  const res = await fetch("http://localhost:8000/predict", {
    method: "POST",
    body: formData,
  });

  const json = await res.json();

  if (json.code !== 200) {
    console.error(json.message);
    return;
  }

  return json.data;
}
```

### 展示标注图示例

```javascript
const { annotated_image_base64 } = data;
document.getElementById("result-img").src =
  `data:image/png;base64,${annotated_image_base64}`;
```

### 宏量营养素饼图数据映射

`totals` 字段可直接映射为饼图数据，热量比例建议按以下换算系数显示：

| 营养素 | 每克热量 |
| --- | --- |
| 碳水化合物 | 4 kcal/g |
| 蛋白质 | 4 kcal/g |
| 脂肪 | 9 kcal/g |

```javascript
const { carbs_g, protein_g, fat_g } = data.totals;
const pieData = [
  { label: "碳水", value: carbs_g * 4 },
  { label: "蛋白质", value: protein_g * 4 },
  { label: "脂肪", value: fat_g * 9 },
];
```

### 建议的前端展示结构

```
上传区域（拖拽 / 点击选择）
    ↓ 上传后
加载动画（调用 /predict 期间）
    ↓ 返回后
┌─────────────────────────────────┐
│  标注结果图（annotated_image）    │
├──────────────┬──────────────────┤
│  食材列表表格  │  宏量营养素饼图   │
│  （ingredients）│  （totals）      │
├──────────────┴──────────────────┤
│  营养合计行（totals）             │
└─────────────────────────────────┘
```

---

## 7. 变更记录

| 版本 | 时间 | 修改人 | 变更内容 |
| --- | --- | --- | --- |
| V1.1.0 | 2026/03/28 | Keming | 增加 display_name、image_info 字段；补充前端对接示例；完善错误码表 |
| V1.0.0 | 2026/03/28 | Keming | 创建初始版本，定义三个接口基本结构 |
