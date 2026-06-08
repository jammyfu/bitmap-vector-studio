from __future__ import annotations

from dataclasses import replace
from typing import Any

from .models import TraceOptions

# Presets are tuned to mimic the mental model of Illustrator Image Trace presets,
# while still exposing VTracer's actual algorithm knobs.
PRESETS: dict[str, TraceOptions] = {
    "bw": TraceOptions(
        colormode="binary",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=6,
        color_precision=6,
        layer_difference=16,
        corner_threshold=55,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
        denoise=True,
    ),
    "poster": TraceOptions(
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=4,
        color_precision=6,
        layer_difference=16,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=10,
        splice_threshold=45,
        path_precision=3,
    ),
    "photo": TraceOptions(
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=2,
        color_precision=8,
        layer_difference=8,
        corner_threshold=70,
        length_threshold=3.5,
        max_iterations=15,
        splice_threshold=35,
        path_precision=4,
        max_input_side=2400,
    ),
    "logo": TraceOptions(
        colormode="color",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=2,
        color_precision=7,
        layer_difference=24,
        corner_threshold=55,
        length_threshold=4.0,
        max_iterations=12,
        splice_threshold=40,
        path_precision=3,
        denoise=True,
    ),
    "pixel_art": TraceOptions(
        colormode="color",
        hierarchical="stacked",
        mode="pixel",
        filter_speckle=0,
        color_precision=8,
        layer_difference=4,
        corner_threshold=60,
        length_threshold=4.0,
        max_iterations=5,
        splice_threshold=45,
        path_precision=1,
        alpha_background="#ffffff",
    ),
    "scan": TraceOptions(
        colormode="binary",
        hierarchical="stacked",
        mode="spline",
        filter_speckle=8,
        color_precision=6,
        layer_difference=16,
        corner_threshold=50,
        length_threshold=4.5,
        max_iterations=10,
        splice_threshold=50,
        path_precision=3,
        denoise=True,
        max_input_side=3000,
    ),
}


def get_preset(name: str) -> TraceOptions:
    key = name.strip().lower().replace("-", "_")
    try:
        return PRESETS[key]
    except KeyError as exc:
        valid = ", ".join(sorted(PRESETS))
        raise ValueError(f"Unknown preset '{name}'. Valid presets: {valid}.") from exc


def options_from_preset(name: str, overrides: dict[str, Any] | None = None) -> TraceOptions:
    base = TraceOptions() if name == "custom" else get_preset(name)
    if not overrides:
        return base.validate()
    clean = {k: v for k, v in overrides.items() if v is not None}
    return replace(base, **clean).validate()
