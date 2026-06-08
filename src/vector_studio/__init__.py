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

from .smart_background import (
    detect_background_color,
    remove_background,
    is_likely_logo,
)
from .enhance import (
    edge_enhance,
    scan_denoise,
    auto_contrast,
    sharpen,
    adaptive_enhance,
)
from .smart_recommend import (
    analyze_image_features,
    recommend_preset,
    recommend_for_image,
)
from .svg_optimizer import (
    merge_same_color_paths,
    merge_similar_colors,
    simplify_path_data,
    svg_quality_score,
    optimize_svg_comprehensive,
)
from .param_search import (
    ParamGrid,
    search_best_params,
    quick_search,
    score_result,
)
from .task_queue import (
    ConversionTask,
    TaskQueue,
)

from .plugin_interface import Plugin
from .plugins import PluginManager
from .config import Config
from .api_client import VectorStudioClient

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
    # Smart background (v0.3)
    "detect_background_color",
    "remove_background",
    "is_likely_logo",
    # Enhance (v0.3)
    "edge_enhance",
    "scan_denoise",
    "auto_contrast",
    "sharpen",
    "adaptive_enhance",
    # Smart recommend (v0.3)
    "analyze_image_features",
    "recommend_preset",
    "recommend_for_image",
    # SVG optimizer (v0.3)
    "merge_same_color_paths",
    "merge_similar_colors",
    "simplify_path_data",
    "svg_quality_score",
    "optimize_svg_comprehensive",
    # Param search (v0.3)
    "ParamGrid",
    "search_best_params",
    "quick_search",
    "score_result",
    # Task queue (v0.3)
    "ConversionTask",
    "TaskQueue",
    # Plugin system (v0.4)
    "Plugin",
    "PluginManager",
    # Config (v0.4)
    "Config",
    # API client (v0.4)
    "VectorStudioClient",
    # AI simplify (v0.5)
    "semantic_simplify",
    "superpixel_simplify",
    "cartoon_effect",
    "adaptive_simplify",
    # AI OCR (v0.5)
    "detect_text_regions",
    "recognize_text",
    "integrate_text_to_svg",
    # AI OCR multi-language (v0.6)
    "detect_language",
    "recognize_text_multilang",
    "detect_vertical_text",
    "create_text_overlay_svg_multilang",
    "preprocess_for_ocr",
    # OCR languages (v0.6)
    "OCR_LANGUAGE_CONFIG",
    "get_tesseract_languages",
    "check_language_available",
    "suggest_language_pack",
    "normalize_language_code",
    "get_language_config",
    # Live preview (v0.5)
    "LivePreviewEngine",
    "PreviewCache",
    # Region trace (v0.5)
    "RegionSelector",
    "region_trace",
    "trace_region",
    "merge_region_svg",
    # Market (v0.5)
    "PresetMarket",
    "MarketBackend",
    "GitHubGistBackend",
    "GitHubRepoBackend",
    "MultiBackend",
]

from .ai_simplify import (
    semantic_simplify,
    superpixel_simplify,
    cartoon_effect,
    adaptive_simplify,
)
from .ai_ocr import (
    detect_text_regions,
    recognize_text,
    integrate_text_to_svg,
    detect_language,
    recognize_text_multilang,
    detect_vertical_text,
    create_text_overlay_svg_multilang,
    preprocess_for_ocr,
)
from .ocr_languages import (
    OCR_LANGUAGE_CONFIG,
    get_tesseract_languages,
    check_language_available,
    suggest_language_pack,
    normalize_language_code,
    get_language_config,
)
from .live_preview import (
    LivePreviewEngine,
    PreviewCache,
)
from .region_trace import (
    RegionSelector,
    region_trace,
    trace_region,
    merge_region_svg,
)
from .market import (
    PresetMarket,
    MarketBackend,
    GitHubGistBackend,
    GitHubRepoBackend,
    MultiBackend,
)

__version__ = "1.1.0"
