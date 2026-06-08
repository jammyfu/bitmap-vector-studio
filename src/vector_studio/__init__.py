"""Bitmap Vector Studio: VTracer-powered raster-to-vector conversion toolkit."""

from .models import TraceOptions, TraceResult
from .presets import PRESETS, get_preset, options_from_preset
from .tracer import trace_image

# New public APIs in v0.2.0
from .preset_manager import (
    save_preset,
    load_preset,
    delete_preset,
    get_all_presets,
    list_user_presets,
)
from .history import (
    record_task,
    get_recent_tasks,
    get_task_options,
)
from .external_editors import (
    detect_editors,
    get_default_editor,
    open_with_editor,
    open_with_default_editor,
)
from .svg_tools import (
    optimize_svg_text,
    optimize_svg_file,
    svg_stats,
    name_svg_layers,
    analyze_svg_structure,
    extract_color_palette,
    suggest_optimization,
)

__all__ = [
    # Core
    "TraceOptions",
    "TraceResult",
    "PRESETS",
    "get_preset",
    "options_from_preset",
    "trace_image",
    # Preset manager
    "save_preset",
    "load_preset",
    "delete_preset",
    "get_all_presets",
    "list_user_presets",
    # History
    "record_task",
    "get_recent_tasks",
    "get_task_options",
    # External editors
    "detect_editors",
    "get_default_editor",
    "open_with_editor",
    "open_with_default_editor",
    # SVG tools
    "optimize_svg_text",
    "optimize_svg_file",
    "svg_stats",
    "name_svg_layers",
    "analyze_svg_structure",
    "extract_color_palette",
    "suggest_optimization",
]

__version__ = "0.2.0"
