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
# i18n
# ---------------------------------------------------------------------------

TRANSLATIONS = {
    'zh-CN': {
        'page.convert.title': '🎨 Bitmap Vector Studio',
        'page.convert.caption': '位图转矢量工具 — 上传、调整、转换',
        'page.convert.upload': '1. 上传图片',
        'page.convert.uploader': '拖拽图片到此处或点击选择文件',
        'page.convert.current_file': '当前文件',
        'page.convert.analyzing': '正在智能分析图片…',
        'page.convert.analysis_fail': '智能分析失败',
        'page.convert.recommend': '智能推荐',
        'page.convert.apply': '应用推荐',
        'page.convert.apply_success': "已应用推荐预设 '{}'",
        'page.convert.apply_unavailable': "推荐预设 '{}' 不可用",
        'page.convert.logo_detected': '检测到 Logo 特征，将自动移除背景',
        'page.convert.adjust': '2. 调整参数',
        'page.convert.preset': '预设',
        'page.convert.colormode': '颜色模式',
        'page.convert.curvemode': '曲线模式',
        'page.convert.optimize': '优化级别',
        'page.convert.optimize.basic': '基础',
        'page.convert.optimize.comprehensive': '综合',
        'page.convert.optimize.aggressive': '激进',
        'page.convert.advanced': '▼ 高级参数',
        'page.convert.filter_speckle': '滤斑点',
        'page.convert.color_precision': '颜色精度',
        'page.convert.layer_difference': '层级间隔',
        'page.convert.corner_threshold': '角点阈值',
        'page.convert.length_threshold': '曲线段长',
        'page.convert.splice_threshold': '拼接阈值',
        'page.convert.path_precision': '路径精度',
        'page.convert.max_iterations': '最大迭代',
        'page.convert.denoise': '轻度降噪',
        'page.convert.smart_bg': '智能背景透明',
        'page.convert.enhance': '图像增强',
        'page.convert.enhance_type': '增强类型',
        'page.convert.ai_simplify': 'AI语义简化',
        'page.convert.simplify_type': '简化类型',
        'page.convert.ai_ocr': 'OCR文字识别',
        'page.convert.max_input_side': '限制输入最大边长',
        'page.convert.max_input_side_px': '最大边长 px',
        'page.convert.posterize': '先做颜色 Posterize',
        'page.convert.posterize_bits': 'Posterize bits',
        'page.convert.start': '3. 开始转换',
        'page.convert.start_btn': '▶ 开始转换',
        'page.convert.converting': '正在转换 SVG…',
        'page.convert.success': '转换完成！',
        'page.convert.error': '转换失败',
        'page.convert.result': '📊 转换结果',
        'page.convert.metric_engine': '引擎',
        'page.convert.metric_elapsed': '耗时',
        'page.convert.metric_paths': '路径数',
        'page.convert.metric_size': '文件大小',
        'page.convert.quality_score': 'SVG 质量评分',
        'page.convert.download': '⬇ 下载 SVG',
        'page.convert.preview': '▼ SVG 预览',
        'page.convert.clear': '🗑 清除结果',
        'page.convert.no_upload': '请上传图片开始转换。支持 PNG、JPG、WEBP、BMP、TIFF 格式。',
        'page.batch.title': '📁 批量转换',
        'page.batch.caption': '一次性转换多张图片',
        'page.batch.file_uploader': '选择多个图片文件',
        'page.batch.selected': '已选择 {count} 个文件',
        'page.batch.start_btn': '▶ 开始批量转换',
        'page.batch.preparing': '准备转换…',
        'page.batch.converting': '正在转换 {name}…',
        'page.batch.done': '批量转换完成',
        'page.batch.summary': '批量转换完成: {success}/{total} 成功',
        'page.batch.result_list': '结果列表',
        'page.batch.download': '下载',
        'page.batch.reuse': '复用参数',
        'page.batch.reuse_success': '已加载 {name} 的参数',
        'page.batch.clear': '🗑 清空批量结果',
        'page.history.title': '🕐 历史记录',
        'page.history.caption': '最近转换任务',
        'page.history.empty': '暂无历史记录',
        'page.history.recent': '最近 {count} 条记录',
        'page.history.preset': '预设',
        'page.history.elapsed': '耗时',
        'page.history.paths': '路径',
        'page.history.reuse': '复用参数',
        'page.history.load_success': '已加载历史任务参数',
        'page.history.load_fail': '加载失败',
        'page.history.clear': '🗑 清空历史记录',
        'page.history.clear_success': '历史记录已清空',
        'page.history.clear_fail': '清空失败',
        'page.settings.title': '⚙️ 设置',
        'page.settings.caption': '偏好配置',
        'page.settings.appearance': '外观',
        'page.settings.theme': '主题',
        'page.settings.defaults': '默认参数',
        'page.settings.default_preset': '默认预设',
        'page.settings.default_optimize': '默认优化级别',
        'page.settings.default_format': '默认输出格式',
        'page.settings.editor': '外部编辑器',
        'page.settings.editor_default': '系统默认',
        'page.settings.editor_unavailable': '外部编辑器检测不可用',
        'page.settings.editor_preference': '首选编辑器',
        'page.settings.language': '语言',
        'page.settings.language_hint': '（语言切换将在重启后生效）',
        'page.settings.save': '💾 保存设置',
        'page.settings.save_success': '设置已保存',
        'page.settings.save_fail': '保存失败',
        'page.settings.save_unavailable': '配置模块不可用，设置仅当前会话有效',
        'page.settings.reset': '🔄 恢复默认设置',
        'page.settings.reset_success': '已恢复默认设置',
        'page.settings.reset_fail': '恢复失败',
        'page.settings.reset_unavailable': '配置模块不可用',
    },
    'en-US': {
        'page.convert.title': '🎨 Bitmap Vector Studio',
        'page.convert.caption': 'Bitmap to Vector — Upload, Adjust, Convert',
        'page.convert.upload': '1. Upload Image',
        'page.convert.uploader': 'Drag image here or click to select',
        'page.convert.current_file': 'Current file',
        'page.convert.analyzing': 'Analyzing image…',
        'page.convert.analysis_fail': 'Smart analysis failed',
        'page.convert.recommend': 'Smart Recommend',
        'page.convert.apply': 'Apply',
        'page.convert.apply_success': "Applied recommended preset '{}'",
        'page.convert.apply_unavailable': "Recommended preset '{}' is unavailable",
        'page.convert.logo_detected': 'Logo features detected, background will be auto-removed',
        'page.convert.adjust': '2. Adjust Parameters',
        'page.convert.preset': 'Preset',
        'page.convert.colormode': 'Color Mode',
        'page.convert.curvemode': 'Curve Mode',
        'page.convert.optimize': 'Optimize Level',
        'page.convert.optimize.basic': 'Basic',
        'page.convert.optimize.comprehensive': 'Comprehensive',
        'page.convert.optimize.aggressive': 'Aggressive',
        'page.convert.advanced': '▼ Advanced',
        'page.convert.filter_speckle': 'Filter Speckle',
        'page.convert.color_precision': 'Color Precision',
        'page.convert.layer_difference': 'Layer Difference',
        'page.convert.corner_threshold': 'Corner Threshold',
        'page.convert.length_threshold': 'Length Threshold',
        'page.convert.splice_threshold': 'Splice Threshold',
        'page.convert.path_precision': 'Path Precision',
        'page.convert.max_iterations': 'Max Iterations',
        'page.convert.denoise': 'Light Denoise',
        'page.convert.smart_bg': 'Smart Background Removal',
        'page.convert.enhance': 'Image Enhancement',
        'page.convert.enhance_type': 'Enhance Type',
        'page.convert.ai_simplify': 'AI Semantic Simplify',
        'page.convert.simplify_type': 'Simplify Type',
        'page.convert.ai_ocr': 'OCR Text Recognition',
        'page.convert.max_input_side': 'Limit Max Input Side',
        'page.convert.max_input_side_px': 'Max side px',
        'page.convert.posterize': 'Posterize First',
        'page.convert.posterize_bits': 'Posterize bits',
        'page.convert.start': '3. Start Conversion',
        'page.convert.start_btn': '▶ Start Conversion',
        'page.convert.converting': 'Converting SVG…',
        'page.convert.success': 'Conversion complete!',
        'page.convert.error': 'Conversion failed',
        'page.convert.result': '📊 Conversion Result',
        'page.convert.metric_engine': 'Engine',
        'page.convert.metric_elapsed': 'Elapsed',
        'page.convert.metric_paths': 'Paths',
        'page.convert.metric_size': 'File Size',
        'page.convert.quality_score': 'SVG Quality Score',
        'page.convert.download': '⬇ Download SVG',
        'page.convert.preview': '▼ SVG Preview',
        'page.convert.clear': '🗑 Clear Result',
        'page.convert.no_upload': 'Please upload an image to start. Supports PNG, JPG, WEBP, BMP, TIFF.',
        'page.batch.title': '📁 Batch Conversion',
        'page.batch.caption': 'Convert multiple images at once',
        'page.batch.file_uploader': 'Select multiple image files',
        'page.batch.selected': '{count} files selected',
        'page.batch.start_btn': '▶ Start Batch Conversion',
        'page.batch.preparing': 'Preparing…',
        'page.batch.converting': 'Converting {name}…',
        'page.batch.done': 'Batch conversion complete',
        'page.batch.summary': 'Batch complete: {success}/{total} succeeded',
        'page.batch.result_list': 'Results',
        'page.batch.download': 'Download',
        'page.batch.reuse': 'Reuse Params',
        'page.batch.reuse_success': 'Loaded params for {name}',
        'page.batch.clear': '🗑 Clear Batch Results',
        'page.history.title': '🕐 History',
        'page.history.caption': 'Recent conversion tasks',
        'page.history.empty': 'No history yet',
        'page.history.recent': 'Recent {count} records',
        'page.history.preset': 'Preset',
        'page.history.elapsed': 'Elapsed',
        'page.history.paths': 'Paths',
        'page.history.reuse': 'Reuse Params',
        'page.history.load_success': 'Loaded historical task params',
        'page.history.load_fail': 'Load failed',
        'page.history.clear': '🗑 Clear History',
        'page.history.clear_success': 'History cleared',
        'page.history.clear_fail': 'Clear failed',
        'page.settings.title': '⚙️ Settings',
        'page.settings.caption': 'Preferences',
        'page.settings.appearance': 'Appearance',
        'page.settings.theme': 'Theme',
        'page.settings.defaults': 'Defaults',
        'page.settings.default_preset': 'Default Preset',
        'page.settings.default_optimize': 'Default Optimize Level',
        'page.settings.default_format': 'Default Output Format',
        'page.settings.editor': 'External Editor',
        'page.settings.editor_default': 'System Default',
        'page.settings.editor_unavailable': 'External editor detection unavailable',
        'page.settings.editor_preference': 'Preferred Editor',
        'page.settings.language': 'Language',
        'page.settings.language_hint': '(Language change takes effect after restart)',
        'page.settings.save': '💾 Save Settings',
        'page.settings.save_success': 'Settings saved',
        'page.settings.save_fail': 'Save failed',
        'page.settings.save_unavailable': 'Config module unavailable, settings valid for this session only',
        'page.settings.reset': '🔄 Reset to Defaults',
        'page.settings.reset_success': 'Reset to defaults',
        'page.settings.reset_fail': 'Reset failed',
        'page.settings.reset_unavailable': 'Config module unavailable',
    },
}


def st_t(key: str, lang: str = 'zh-CN') -> str:
    """Streamlit page translation helper."""
    return TRANSLATIONS.get(lang, TRANSLATIONS['zh-CN']).get(key, key)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def init_session_state() -> None:
    """Initialize default session-state values once."""
    if "initialized" in st.session_state:
        return

    apply_preset_values("poster")
    st.session_state.initialized = True
    st.session_state.language = 'zh-CN'

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
