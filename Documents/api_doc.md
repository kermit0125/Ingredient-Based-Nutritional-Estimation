# API 接口说明 · 食材营养识别后端

**版本**：V1.2.0  
**最后更新**：2026/04/04  
**说明**：下文与当前实现 `backend/api/main.py` 一致。响应体为**扁平 JSON**，不再使用外层 `code` / `message` / `data` 包装（若前端曾按旧文档解析，需改为直接读字段或使用 HTTP 状态码）。

**本地 Base URL**：`http://127.0.0.1:8000`（示例端口 8000，以实际 `uvicorn` 为准）

---

## 目录

1. [通用约定](#1-通用约定)
2. [GET /health](#2-get-health)
3. [GET /classes](#3-get-classes)
4. [POST /predict](#4-post-predict)
5. [错误与 HTTP 状态](#5-错误与-http-状态)
6. [前端对接提示](#6-前端对接提示)
7. [变更记录](#7-变更记录)

---

## 1. 通用约定

### 请求

- `POST /predict`：`multipart/form-data`，字段名 `image`（文件）。

### 响应

- 成功时：各接口返回 JSON 对象，字段见各节；**无统一外层信封**。
- 失败时：FastAPI 默认 `{"detail": "<错误描述>"}`，HTTP 状态码 4xx/5xx。

### 图片限制（实现侧）

| 项目 | 限制 |
|------|------|
| 格式 | JPG、PNG（`Content-Type` 异常时可尝试 `application/octet-stream`） |
| 最大体积 | 10 MB |
| 过小图 | 不拒绝；服务端可记日志，建议前端提示 ≥300×300 |

### 单位

| 含义 | 单位 |
|------|------|
| 重量 | 克（g） |
| 热量 | 千卡（kcal） |
| 碳水 / 蛋白质 / 脂肪 | 克（g） |
| 置信度 | 0–1 浮点 |
| bbox | 像素，原图坐标 `[x1,y1,x2,y2]` |
| mask_area_ratio | 0–1，掩码或框面积 / 原图宽高积 |

### 环境变量（可选）

| 变量 | 说明 |
|------|------|
| `INE_SEG_WEIGHTS` | 推理用 `.pt` 路径（绝对或与 `backend` 相对的相对路径） |
| `INE_CONF` | 置信度阈值，默认 `0.5` |

未设置 `INE_SEG_WEIGHTS` 时，默认使用 `backend/runs/segment/exp1/weights/best.pt`（若文件不存在则 `503`）。

---

## 2. GET /health

### 响应示例

```json
{
  "status": "ok"
}
```

### 前端演示页

- `GET /`：返回内置 Web 前端页面，用于上传食材图片并联调 `/predict`
- `GET /static/...`：前端静态资源（HTML 引用的 CSS / JS）

---

## 3. GET /classes

返回 canonical 类别名列表及各类参考克重（与 `nutrition/reference_weights.py` 一致；未配置则为 `null`）。

### 响应示例

```json
{
  "classes": [
    "bell_pepper",
    "tomato",
    "onion",
    "potato",
    "mushroom",
    "carrot",
    "broccoli",
    "cucumber",
    "corn",
    "egg"
  ],
  "reference_weight_g": {
    "bell_pepper": 220.0,
    "tomato": 180.0,
    "onion": 200.0,
    "potato": 280.0,
    "mushroom": 150.0,
    "carrot": 160.0,
    "broccoli": 250.0,
    "cucumber": 200.0,
    "corn": 220.0,
    "egg": 60.0
  }
}
```

### 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| classes | string[] | 与 `configs/classes.yaml` 中顺序一致 |
| reference_weight_g | object | 键为类别名，值为参考克重（g），用于面积比估重 |

---

## 4. POST /predict

调用 `models/inference.run_predict`，返回实例列表、合计、标注图 base64；无检出或过滤后为空时带 `message`。

### 请求

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| image | file | 是 | JPG/PNG |

### 响应示例（有检出）

```json
{
  "ingredients": [
    {
      "class": "tomato",
      "confidence": 0.8842,
      "bbox": [300, 120, 480, 330],
      "mask_area_ratio": 0.071234,
      "estimated_weight_g": 106.5,
      "calories": 19.2,
      "carbs_g": 4.1,
      "protein_g": 1.0,
      "fat_g": 0.2
    }
  ],
  "totals": {
    "calories": 19.2,
    "carbs_g": 4.1,
    "protein_g": 1.0,
    "fat_g": 0.2
  },
  "annotated_image_base64": "<JPEG Base64>",
  "message": null
}
```

### `ingredients[]` 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| class | string | canonical 类别名（snake_case） |
| confidence | float | 模型置信度 |
| bbox | int[4] | `[x1,y1,x2,y2]` |
| mask_area_ratio | float | 面积比 ri |
| estimated_weight_g | float | 估算克重 |
| calories | float | 该实例热量（kcal） |
| carbs_g / protein_g / fat_g | float | 宏量（g） |
| estimate_note | string | 可选；估重截断、缺营养行等说明 |

### `totals`

全图各实例宏量与热量之和。

### `annotated_image_base64`

- JPEG 编码的标注图（掩码+框+标签），非 PNG。  
- 前端示例：`data:image/jpeg;base64,${annotated_image_base64}`

### 无有效实例时

`ingredients` 为空数组，`totals` 各量为 0，`message` 为中文提示字符串（如未识别到食材），`annotated_image_base64` 为原图 JPEG。

---

## 5. 错误与 HTTP 状态

| HTTP | 响应体 | 典型原因 |
|------|--------|----------|
| 400 | `{"detail": "..."}` | 非 JPG/PNG、解码失败、超过 10MB |
| 500 | `{"detail": "系统异常，请联系开发者"}` | 推理未捕获异常 |
| 503 | `{"detail": "分割模型未就绪..."}` | 默认或 `INE_SEG_WEIGHTS` 指向的权重文件不存在 |

---

## 6. 前端对接提示

### 上传示例（fetch）

```javascript
async function predict(file) {
  const formData = new FormData();
  formData.append("image", file);
  const res = await fetch("http://127.0.0.1:8000/predict", {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}
```

### 展示标注图

```javascript
const { annotated_image_base64 } = data;
img.src = `data:image/jpeg;base64,${annotated_image_base64}`;
```

### 展示名映射

接口不返回 `display_name`。若需中文名，请在前端维护 `class` → 中文对照表，或扩展后端另行约定。

### 饼图（近似）

可用 `totals` 中克重 × Atwater 系数估算各宏量贡献热量，仅作展示参考。

---

## 7. 变更记录

| 版本 | 时间 | 变更内容 |
|------|------|----------|
| V1.2.0 | 2026/04/04 | 与 `api/main.py` 对齐：扁平 JSON、/health、/classes、/predict 字段；JPEG 标注图；错误体 `detail`；环境变量说明 |
| V1.1.0 | 2026/03/28 | 曾约定 code/message/data 包装及扩展字段（与当前实现不一致，已废弃） |
| V1.0.0 | 2026/03/28 | 初稿 |
