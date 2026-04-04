from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_NUTRITION_CSV = BACKEND_ROOT / "data" / "nutrition_table.csv"


@dataclass(frozen=True)
class NutritionTable:
    rows: dict[str, dict[str, float]]


def load_nutrition_table(path: Path | None = None) -> NutritionTable:
    p = path or DEFAULT_NUTRITION_CSV
    if not p.is_file():
        raise FileNotFoundError(f"Missing nutrition table: {p}")
    rows: dict[str, dict[str, float]] = {}
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("canonical_name") or "").strip()
            if not name:
                continue
            rows[name] = {
                "calories_kcal": float(row["calories_kcal"]),
                "carbohydrate_g": float(row["carbohydrate_g"]),
                "protein_g": float(row["protein_g"]),
                "fat_g": float(row["fat_g"]),
            }
    return NutritionTable(rows=rows)


def macros_for_weight(table: NutritionTable, class_name: str, weight_g: float) -> dict[str, float] | None:
    per = table.rows.get(class_name)
    if per is None:
        return None
    scale = max(0.0, float(weight_g)) / 100.0
    return {
        "calories": round(per["calories_kcal"] * scale, 2),
        "carbs_g": round(per["carbohydrate_g"] * scale, 3),
        "protein_g": round(per["protein_g"] * scale, 3),
        "fat_g": round(per["fat_g"] * scale, 3),
    }
