"""Bitmap Vector Studio: VTracer-powered raster-to-vector conversion toolkit."""

from .models import TraceOptions, TraceResult
from .presets import PRESETS, get_preset, options_from_preset
from .tracer import trace_image

__all__ = [
    "TraceOptions",
    "TraceResult",
    "PRESETS",
    "get_preset",
    "options_from_preset",
    "trace_image",
]

__version__ = "0.1.0"
