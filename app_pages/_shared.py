"""Shared helpers and session-state initialization for Streamlit pages."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from vector_studio.models import TraceOptions
from vector_studio.presets import PRESETS
from vector_studio.preset_manager import (
    get_all_presets,
    save_preset,
    delete_preset,
    list_user_presets,
    preset_exists,
)
from vector_studio.history import (
    record_task,
    get_recent_tasks,
    get_task_options,
    clear_history,
)
from vector_studio.tracer import trace_image

# Graceful degradation imports
try:
    from vector_studio.smart_recommend import recommend_for_image, analyze_image_features

    _HAS_SMART_RECOMMEND = True
except Exception:
    _HAS_SMART_RECOMMEND = False

try:
    from vector_studio.smart_background import is_likely_logo, remove_background

    _HAS_SMART_BG = True
except Exception:
    _HAS_SMART_BG = False

try:
    from vector_studio.enhance import adaptive_enhance

    _HAS_ENHANCE = True
except Exception:
    _HAS_ENHANCE = False

try:
    from vector_studio.svg_optimizer import optimize_svg_comprehensive, svg_quality_score

    _HAS_SVG_OPTIMIZER = True
except Exception:
    _HAS_SVG_OPTIMIZER = False

try:
    from vector_studio.ai_simplify import adaptive_simplify

    _HAS_AI_SIMPLIFY = True
except Exception:
    _HAS_AI_SIMPLIFY = False

try:
    from vector_studio.ai_ocr import detect_text_regions, recognize_text

    _HAS_AI_OCR = True
except Exception:
    _HAS_AI_OCR = False

try:
    from vector_studio.config import Config

    _HAS_CONFIG = True
except Exception:
    _HAS_CONFIG = False

try:
    from vector_studio.external_editors import (
        detect_editors,
        open_with_editor,
        EditorNotFoundError,
        EditorOpenError,
    )

    _HAS_EDITORS = True
except Exception:
    _HAS_EDITORS = False

BUILTIN_PRESET_NAMES = {"bw", "poster", "photo", "logo", "pixel_art", "scan"}


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def init_session_state() -> None:
    """Initialize default session-state values once."""
    if "initialized" in st.session_state:
        return

    apply_preset_values("poster")
    st.session_state.initialized = True

    # Smart features
    st.session_state.smart_remove_bg = False
    st.session_state.enhance_enabled = False
    st.session_state.enhance_type = "auto"
    st.session_state.optimize_level = "basic"
    st.session_state.ai_simplify_enabled = False
    st.session_state.ai_simplify_type = "auto"
    st.session_state.ai_ocr_enabled = False
    st.session_state.ai_ocr_regions = None

    # Advanced params
    st.session_state.max_input_side_enabled = False
    st.session_state.max_input_side = 2400
    st.session_state.posterize_enabled = False
    st.session_state.posterize = 6
    st.session_state.denoise = False

    # Batch / results
    st.session_state.batch_running = False
    st.session_state.batch_results = []

    # UI
    st.session_state.theme = "light"


def apply_preset_values(preset_name: str) -> None:
    """Write preset parameters into session_state so widgets auto-update."""
    try:
        presets = get_all_presets()
    except Exception:
        presets = PRESETS
    opts = presets.get(preset_name, PRESETS.get("poster"))
    if opts is None:
        opts = TraceOptions()

    st.session_state.preset_selector = preset_name
    st.session_state.colormode = opts.colormode
    st.session_state.hierarchical = opts.hierarchical
    st.session_state.mode = opts.mode
    st.session_state.filter_speckle = int(opts.filter_speckle)
    st.session_state.color_precision = int(opts.color_precision)
    st.session_state.layer_difference = int(opts.layer_difference)
    st.session_state.corner_threshold = int(opts.corner_threshold)
    st.session_state.length_threshold = float(opts.length_threshold)
    st.session_state.splice_threshold = int(opts.splice_threshold)
    st.session_state.path_precision = int(opts.path_precision)
    st.session_state.max_iterations = int(opts.max_iterations)
    st.session_state.denoise = bool(opts.denoise)
    st.session_state.max_input_side_enabled = opts.max_input_side is not None
    st.session_state.max_input_side = int(opts.max_input_side or 2400)
    st.session_state.posterize_enabled = opts.posterize is not None
    st.session_state.posterize = int(opts.posterize or 6)


def build_options_from_state() -> TraceOptions:
    """Reconstruct TraceOptions from current session_state."""
    return TraceOptions(
        colormode=st.session_state.colormode,
        hierarchical=st.session_state.hierarchical,
        mode=st.session_state.mode,
        filter_speckle=int(st.session_state.filter_speckle),
        color_precision=int(st.session_state.color_precision),
        layer_difference=int(st.session_state.layer_difference),
        corner_threshold=int(st.session_state.corner_threshold),
        length_threshold=float(st.session_state.length_threshold),
        max_iterations=int(st.session_state.max_iterations),
        splice_threshold=int(st.session_state.splice_threshold),
        path_precision=int(st.session_state.path_precision),
        denoise=bool(st.session_state.denoise),
        max_input_side=int(st.session_state.max_input_side)
        if st.session_state.max_input_side_enabled
        else None,
        posterize=int(st.session_state.posterize) if st.session_state.posterize_enabled else None,
    ).validate()


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------


def get_preset_options() -> list[str]:
    """Return all preset names, built-ins first."""
    try:
        all_presets = get_all_presets()
    except Exception:
        all_presets = PRESETS
    built_ins = [p for p in all_presets if p in BUILTIN_PRESET_NAMES]
    customs = [p for p in all_presets if p not in BUILTIN_PRESET_NAMES]
    return built_ins + customs


def format_preset_name(name: str) -> str:
    """Add icon prefix to distinguish built-in vs user preset."""
    if name in BUILTIN_PRESET_NAMES:
        return f"🏭 {name}"
    return f"👤 {name}"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def save_uploaded_file(uploaded_file, tmp_dir: Path) -> Path:
    """Persist a Streamlit UploadedFile to disk."""
    suffix = Path(uploaded_file.name).suffix or ".png"
    dest = tmp_dir / f"upload{suffix}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def color_for_score(score: float) -> str:
    """Emoji color indicator for quality score."""
    if score >= 80:
        return "🟢"
    elif score >= 60:
        return "🟡"
    return "🔴"


def show_ui_message() -> None:
    """Render pending toast messages stored in session_state."""
    if "ui_message" not in st.session_state:
        return
    msg_type, msg_text = st.session_state.pop("ui_message")
    if msg_type == "success":
        st.toast(msg_text, icon="✅")
    elif msg_type == "error":
        st.toast(msg_text, icon="❌")
    elif msg_type == "warning":
        st.toast(msg_text, icon="⚠️")


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def get_config() -> "Config | None":
    """Load or return cached Config."""
    if not _HAS_CONFIG:
        return None
    if "app_config" not in st.session_state or st.session_state.app_config is None:
        try:
            st.session_state.app_config = Config.load()
        except Exception:
            return None
    return st.session_state.app_config


def save_config(cfg: "Config") -> None:
    """Persist config and update cache."""
    try:
        cfg.save()
        st.session_state.app_config = cfg
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"配置保存失败: {e}")
