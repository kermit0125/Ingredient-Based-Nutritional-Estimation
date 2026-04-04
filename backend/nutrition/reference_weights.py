from __future__ import annotations

REFERENCE_WEIGHT_G: dict[str, float] = {
    "bell_pepper": 220.0,
    "tomato": 180.0,
    "onion": 200.0,
    "potato": 280.0,
    "mushroom": 150.0,
    "carrot": 160.0,
    "broccoli": 250.0,
    "cucumber": 200.0,
    "corn": 220.0,
    "egg": 60.0,
}


def get_reference_weight_g(class_name: str) -> float | None:
    return REFERENCE_WEIGHT_G.get(class_name)
