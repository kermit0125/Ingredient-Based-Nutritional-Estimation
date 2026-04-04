from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
_SCRIPTS = BACKEND_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from dataset_common import load_classes_config
from models.inference import DEFAULT_SEG_WEIGHTS, run_predict
from nutrition.reference_weights import REFERENCE_WEIGHT_G

logger = logging.getLogger("ine.api")

app = FastAPI(title="Ingredient Nutrition Estimator", version="1.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _weights_path() -> Path:
    raw = os.environ.get("INE_SEG_WEIGHTS", "").strip()
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else (BACKEND_ROOT / p).resolve()
    return DEFAULT_SEG_WEIGHTS.resolve()


def _conf() -> float:
    try:
        return float(os.environ.get("INE_CONF", "0.5"))
    except ValueError:
        return 0.5


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/classes")
def classes() -> dict:
    cfg = load_classes_config()
    names = cfg["canonical_order"]
    refs = {n: REFERENCE_WEIGHT_G.get(n) for n in names}
    return {"classes": names, "reference_weight_g": refs}


@app.post("/predict")
def predict(image: UploadFile = File(...)) -> dict:
    ct = (image.content_type or "").lower()
    if ct not in ("image/jpeg", "image/jpg", "image/png", "image/x-png", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="请上传 JPG 或 PNG 格式图片")

    data = image.file.read()
    max_bytes = 10 * 1024 * 1024
    if len(data) > max_bytes:
        raise HTTPException(status_code=400, detail="图片超过 10MB 限制")

    arr = np.frombuffer(data, dtype=np.uint8)
    im = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if im is None:
        raise HTTPException(status_code=400, detail="无法解码图片，请确认文件为 JPG/PNG")

    h, w = im.shape[0], im.shape[1]
    if min(h, w) < 300:
        logger.warning("image small: %sx%s", w, h)

    wpath = _weights_path()
    if not wpath.is_file():
        logger.error("missing weights: %s", wpath)
        raise HTTPException(
            status_code=503,
            detail=f"分割模型未就绪，缺少权重文件。请训练后放置或设置 INE_SEG_WEIGHTS: {wpath}",
        )

    try:
        out = run_predict(im, weights=wpath, conf=_conf())
    except Exception as e:
        logger.exception("predict failed: %s", e)
        raise HTTPException(status_code=500, detail="系统异常，请联系开发者") from e

    return out
