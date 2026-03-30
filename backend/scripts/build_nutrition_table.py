"""
从 USDA FoodData Central (FDC) 常见 raw 食材条目汇总每 100g 营养值，写入 data/nutrition_table.csv。
与 configs/classes.yaml 中 canonical 10 类顺序一致；不依赖训练或模型。

运行（在 backend/）:
    python scripts/build_nutrition_table.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = BACKEND_ROOT / "data" / "nutrition_table.csv"

# Canonical 顺序须与 classes.yaml names 0..9 一致。
# 数值来自 USDA 标准参考/常见 FDC 条目（raw），约 100g 可食部分。
USDA_PER_100G = [
    {
        "canonical_name": "bell_pepper",
        "fdc_hint": "Peppers, sweet, green, raw (FDC 168421 等)",
        "calories_kcal": 31,
        "carbohydrate_g": 6.0,
        "protein_g": 1.0,
        "fat_g": 0.3,
    },
    {
        "canonical_name": "tomato",
        "fdc_hint": "Tomatoes, red, raw",
        "calories_kcal": 18,
        "carbohydrate_g": 3.9,
        "protein_g": 0.9,
        "fat_g": 0.2,
    },
    {
        "canonical_name": "onion",
        "fdc_hint": "Onions, raw",
        "calories_kcal": 40,
        "carbohydrate_g": 9.3,
        "protein_g": 1.1,
        "fat_g": 0.1,
    },
    {
        "canonical_name": "potato",
        "fdc_hint": "Potatoes, flesh and skin, raw",
        "calories_kcal": 77,
        "carbohydrate_g": 17.5,
        "protein_g": 2.0,
        "fat_g": 0.1,
    },
    {
        "canonical_name": "mushroom",
        "fdc_hint": "Mushrooms, white, raw",
        "calories_kcal": 22,
        "carbohydrate_g": 3.3,
        "protein_g": 3.1,
        "fat_g": 0.3,
    },
    {
        "canonical_name": "carrot",
        "fdc_hint": "Carrots, raw",
        "calories_kcal": 41,
        "carbohydrate_g": 9.6,
        "protein_g": 0.9,
        "fat_g": 0.2,
    },
    {
        "canonical_name": "broccoli",
        "fdc_hint": "Broccoli, raw",
        "calories_kcal": 34,
        "carbohydrate_g": 7.0,
        "protein_g": 2.8,
        "fat_g": 0.4,
    },
    {
        "canonical_name": "cucumber",
        "fdc_hint": "Cucumber, with peel, raw",
        "calories_kcal": 15,
        "carbohydrate_g": 3.6,
        "protein_g": 0.7,
        "fat_g": 0.1,
    },
    {
        "canonical_name": "corn",
        "fdc_hint": "Corn, sweet, yellow, raw",
        "calories_kcal": 86,
        "carbohydrate_g": 19.0,
        "protein_g": 3.3,
        "fat_g": 1.4,
    },
    {
        "canonical_name": "egg",
        "fdc_hint": "Egg, whole, raw, fresh",
        "calories_kcal": 143,
        "carbohydrate_g": 1.1,
        "protein_g": 12.6,
        "fat_g": 9.5,
    },
]


def main() -> None:
    fieldnames = [
        "canonical_name",
        "calories_kcal",
        "carbohydrate_g",
        "protein_g",
        "fat_g",
        "usda_fdc_hint",
    ]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for row in USDA_PER_100G:
            w.writerow(row)
    print(f"Wrote {OUT_PATH} ({len(USDA_PER_100G)} classes)")


if __name__ == "__main__":
    main()
