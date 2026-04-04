from __future__ import annotations

from dataclasses import dataclass

from .reference_weights import get_reference_weight_g

MAX_ESTIMATED_WEIGHT_G = 2000.0


@dataclass(frozen=True)
class WeightEstimate:
    mask_area_ratio: float
    estimated_weight_g: float
    reference_weight_g: float | None
    weight_capped: bool
    estimate_note: str | None


def estimate_weight_from_mask_area(
    mask_area_px: int,
    image_width: int,
    image_height: int,
    class_name: str,
) -> WeightEstimate | None:
    if image_width <= 0 or image_height <= 0:
        return None
    denom = float(image_width * image_height)
    if denom <= 0:
        return None
    if mask_area_px <= 0:
        return None

    ri = float(mask_area_px) / denom
    wref = get_reference_weight_g(class_name)
    if wref is None:
        return WeightEstimate(
            mask_area_ratio=ri,
            estimated_weight_g=0.0,
            reference_weight_g=None,
            weight_capped=False,
            estimate_note="营养数据缺失：无参考重量",
        )

    wi = ri * wref
    capped = False
    note = None
    if wi > MAX_ESTIMATED_WEIGHT_G:
        wi = MAX_ESTIMATED_WEIGHT_G
        capped = True
        note = "估重异常：已截断至上限"

    return WeightEstimate(
        mask_area_ratio=ri,
        estimated_weight_g=wi,
        reference_weight_g=wref,
        weight_capped=capped,
        estimate_note=note,
    )
