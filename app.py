from __future__ import annotations

import base64
import html
import json
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

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
from vector_studio.external_editors import (
    detect_editors,
    open_with_editor,
    EditorNotFoundError,
    EditorOpenError,
)
from vector_studio.svg_tools import export_svg_to_pdf, export_svg_to_png
from vector_studio.tracer import trace_image

# v0.3 modules — import with graceful degradation
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
    from vector_studio.param_search import quick_search, search_best_params, ParamGrid

    _HAS_PARAM_SEARCH = True
except Exception:
    _HAS_PARAM_SEARCH = False

try:
    from vector_studio.task_queue import TaskQueue

    _HAS_TASK_QUEUE = True
except Exception:
    _HAS_TASK_QUEUE = False

# v0.4 modules — import with graceful degradation
try:
    from vector_studio.plugins import PluginManager

    _HAS_PLUGINS = True
except Exception:
    _HAS_PLUGINS = False

try:
    from vector_studio.config import Config

    _HAS_CONFIG = True
except Exception:
    _HAS_CONFIG = False

try:
    from vector_studio.api_client import VectorStudioClient

    _HAS_API_CLIENT = True
except Exception:
    _HAS_API_CLIENT = False

# v0.5 modules — import with graceful degradation
try:
    from vector_studio.live_preview import LivePreviewEngine

    _HAS_LIVE_PREVIEW = True
except Exception:
    _HAS_LIVE_PREVIEW = False

try:
    from vector_studio.region_trace import RegionSelector, region_trace

    _HAS_REGION_TRACE = True
except Exception:
    _HAS_REGION_TRACE = False

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
    from vector_studio.market import PresetMarket

    _HAS_MARKET = True
except Exception:
    _HAS_MARKET = False

# v1.1 modules — import with graceful degradation
try:
    from vector_studio.performance import PerformanceMonitor, StreamingImageProcessor

    _HAS_PERFORMANCE = True
except Exception:
    _HAS_PERFORMANCE = False

try:
    from vector_studio.gpu_backend import detect_gpu, gpu_available, GPUBackend

    _HAS_GPU_BACKEND = True
except Exception:
    _HAS_GPU_BACKEND = False

try:
    from vector_studio.startup_optimizer import StartupOptimizer

    _HAS_STARTUP_OPTIMIZER = True
except Exception:
    _HAS_STARTUP_OPTIMIZER = False

try:
    from vector_studio.plugin_hotreload import PluginWatcher

    _HAS_PLUGIN_HOTRELOAD = True
except Exception:
    _HAS_PLUGIN_HOTRELOAD = False

try:
    from vector_studio.checkpoint import CheckpointManager

    _HAS_CHECKPOINT = True
except Exception:
    _HAS_CHECKPOINT = False

try:
    from vector_studio.workspace import WorkspaceManager, Workspace, CrashRecovery

    _HAS_WORKSPACE = True
except Exception:
    _HAS_WORKSPACE = False

try:
    from vector_studio.ocr_languages import get_tesseract_languages, check_language_available

    _HAS_OCR_LANGUAGES = True
except Exception:
    _HAS_OCR_LANGUAGES = False

# v1.2 modules — import with graceful degradation
try:
    from vector_studio.engines import EngineRegistry, EngineBenchmark

    _HAS_ENGINES = True
except Exception:
    _HAS_ENGINES = False

try:
    from vector_studio.plugin_sdk import PluginValidator, PluginScaffold, PluginDebugger

    _HAS_PLUGIN_SDK = True
except Exception:
    _HAS_PLUGIN_SDK = False

try:
    from vector_studio.cloud_sync import CloudSyncManager

    _HAS_CLOUD_SYNC = True
except Exception:
    _HAS_CLOUD_SYNC = False

# v2.0 modules — import with graceful degradation
try:
    from vector_studio.ai_onnx import AIProcessor, ONNXModelManager

    _HAS_AI_ONNX = True
except Exception:
    _HAS_AI_ONNX = False

try:
    from vector_studio.engine_orchestrator import EngineOrchestrator

    _HAS_ENGINE_ORCHESTRATOR = True
except Exception:
    _HAS_ENGINE_ORCHESTRATOR = False

try:
    from vector_studio.collaboration import CollabManager

    _HAS_COLLAB = True
except Exception:
    _HAS_COLLAB = False

try:
    from vector_studio.animation import AnimationBuilder

    _HAS_ANIMATION = True
except Exception:
    _HAS_ANIMATION = False

try:
    from vector_studio.workflow import Workflow, WorkflowEngine

    _HAS_WORKFLOW = True
except Exception:
    _HAS_WORKFLOW = False

try:
    from vector_studio.sync_service import SyncClient

    _HAS_SYNC = True
except Exception:
    _HAS_SYNC = False

st.set_page_config(page_title="Bitmap Vector Studio", page_icon="🖋️", layout="wide")
st.title("Bitmap Vector Studio")
st.caption("VTracer 驱动的 Illustrator-like 位图转 SVG 工具")

BUILTIN_PRESET_NAMES = {"bw", "poster", "photo", "logo", "pixel_art", "scan"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def apply_preset_values(preset_name: str) -> None:
    """将指定预设的参数写入 session_state，使控件自动更新。"""
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
    """从当前 session_state 重建 TraceOptions。"""
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
        max_input_side=int(st.session_state.max_input_side) if st.session_state.max_input_side_enabled else None,
        posterize=int(st.session_state.posterize) if st.session_state.posterize_enabled else None,
    ).validate()


def on_preset_change() -> None:
    """预设下拉框变化时的回调。"""
    apply_preset_values(st.session_state.preset_selector)


def slider_with_value(label: str, min_val, max_val, key: str, step=None, help_text: str | None = None):
    """渲染带实时数值显示的滑块。"""
    c1, c2 = st.columns([4, 1])
    with c1:
        kwargs = {"help": help_text} if help_text else {}
        if step is not None:
            st.slider(label, min_val, max_val, key=key, step=step, **kwargs)
        else:
            st.slider(label, min_val, max_val, key=key, **kwargs)
    with c2:
        st.markdown(
            f"<div style='padding-top:28px;text-align:center;font-weight:bold'>{st.session_state[key]}</div>",
            unsafe_allow_html=True,
        )
    return st.session_state[key]


def get_preset_options() -> list[str]:
    """返回所有预设名称列表，内置在前、用户自定义在后。"""
    try:
        all_presets = get_all_presets()
    except Exception:
        all_presets = PRESETS
    built_ins = [p for p in all_presets if p in BUILTIN_PRESET_NAMES]
    customs = [p for p in all_presets if p not in BUILTIN_PRESET_NAMES]
    return built_ins + customs


def format_preset_name(name: str) -> str:
    """为预设名称添加图标前缀以区分内置/用户预设。"""
    if name in BUILTIN_PRESET_NAMES:
        return f"🏭 {name}"
    return f"👤 {name}"


def extract_svg_layers(svg_text: str) -> list[dict]:
    """尝试从 SVG 中提取 <g> 图层信息。"""
    layers: list[dict] = []
    try:
        root = ET.fromstring(svg_text.encode("utf-8"))
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "g":
                gid = elem.get("id")
                fill = elem.get("fill")
                if gid or fill:
                    layers.append({"id": gid or "", "fill": fill or ""})
    except Exception:
        pass
    # 去重并限制数量
    seen = set()
    unique = []
    for layer in layers:
        key = (layer.get("id"), layer.get("fill"))
        if key not in seen:
            seen.add(key)
            unique.append(layer)
    return unique[:30]


def _save_uploaded_file(uploaded_file, tmp_dir: Path) -> Path:
    """将 Streamlit UploadedFile 保存到临时目录并返回路径。"""
    suffix = Path(uploaded_file.name).suffix or ".png"
    dest = tmp_dir / f"{uploaded_file.file_id or 'upload'}{suffix}"
    dest.write_bytes(uploaded_file.getvalue())
    return dest


def _color_for_score(score: float) -> str:
    """根据评分返回颜色标识。"""
    if score >= 80:
        return "🟢"
    elif score >= 60:
        return "🟡"
    else:
        return "🔴"


def _get_plugin_manager() -> "PluginManager | None":
    """获取或初始化 PluginManager。"""
    if not _HAS_PLUGINS:
        return None
    if "plugin_manager" not in st.session_state or st.session_state.plugin_manager is None:
        pm = PluginManager()
        pm.discover_plugins()
        st.session_state.plugin_manager = pm
    return st.session_state.plugin_manager


def _get_config() -> "Config | None":
    """获取或初始化 Config。"""
    if not _HAS_CONFIG:
        return None
    if "app_config" not in st.session_state or st.session_state.app_config is None:
        cfg = Config.load()
        st.session_state.app_config = cfg
    return st.session_state.app_config


def _get_live_preview_engine() -> "LivePreviewEngine | None":
    """获取或初始化 LivePreviewEngine。"""
    if not _HAS_LIVE_PREVIEW:
        return None
    if "live_preview_engine" not in st.session_state or st.session_state.live_preview_engine is None:
        engine = LivePreviewEngine(max_size=400, cache_size=10)
        st.session_state.live_preview_engine = engine
    return st.session_state.live_preview_engine


def _get_preset_market() -> "PresetMarket | None":
    """获取或初始化 PresetMarket。"""
    if not _HAS_MARKET:
        return None
    if "preset_market" not in st.session_state or st.session_state.preset_market is None:
        market = PresetMarket()
        st.session_state.preset_market = market
    return st.session_state.preset_market


def _hash_options(options: TraceOptions) -> str:
    """为防抖生成参数哈希。"""
    import hashlib
    data = f"{options.vtracer_kwargs()}:{options.max_input_side}:{options.denoise}:{options.posterize}"
    return hashlib.sha256(data.encode("utf-8")).hexdigest()[:16]


def _run_live_preview(input_path: Path, options: TraceOptions) -> bytes | None:
    """生成实时预览字节，带简单速率限制。"""
    engine = _get_live_preview_engine()
    if engine is None:
        return None
    try:
        return engine.generate_preview_bytes(input_path, options)
    except Exception as e:
        st.session_state["ui_message"] = ("warning", f"实时预览失败: {e}")
        return None


def _render_region_overlay(image_bytes: bytes, x: int, y: int, w: int, h: int, mime: str = "image/png") -> str:
    """用 CSS 在原图上叠加选区框的 HTML。"""
    b64 = base64.b64encode(image_bytes).decode()
    return f"""
    <div style="position:relative;display:inline-block;max-width:100%;">
      <img src="data:{mime};base64,{b64}" style="max-width:100%;display:block;">
      <div style="position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;
                  border:2px dashed #ff4444;box-sizing:border-box;pointer-events:none;
                  background:rgba(255,68,68,0.15);">
        <span style="position:absolute;top:-18px;left:0;background:#ff4444;color:white;
                     font-size:11px;padding:1px 4px;border-radius:2px;">选区</span>
      </div>
    </div>
    """


def _save_config(cfg: "Config") -> None:
    """保存配置并更新 session_state。"""
    try:
        cfg.save()
        st.session_state.app_config = cfg
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"配置保存失败: {e}")


def _check_api_health() -> dict | None:
    """检查 API 服务健康状态。"""
    if not _HAS_API_CLIENT:
        return None
    try:
        client = VectorStudioClient("http://localhost:8000")
        return client.health()
    except Exception:
        return None


def _start_api_service() -> subprocess.Popen | None:
    """启动 API 服务子进程。"""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "vector_studio.api:app", "--host", "127.0.0.1", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return proc
    except Exception:
        return None


def _stop_api_service(proc: subprocess.Popen | None) -> None:
    """停止 API 服务子进程。"""
    if proc is None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# v1.1 Helpers
# ---------------------------------------------------------------------------

def _get_performance_monitor() -> "PerformanceMonitor | None":
    """获取或初始化 PerformanceMonitor。"""
    if not _HAS_PERFORMANCE:
        return None
    if "performance_monitor" not in st.session_state or st.session_state.performance_monitor is None:
        st.session_state.performance_monitor = PerformanceMonitor()
    return st.session_state.performance_monitor


def _get_workspace_manager() -> "WorkspaceManager | None":
    """获取或初始化 WorkspaceManager。"""
    if not _HAS_WORKSPACE:
        return None
    if "workspace_manager" not in st.session_state or st.session_state.workspace_manager is None:
        st.session_state.workspace_manager = WorkspaceManager()
    return st.session_state.workspace_manager


def _get_checkpoint_manager() -> "CheckpointManager | None":
    """获取或初始化 CheckpointManager。"""
    if not _HAS_CHECKPOINT:
        return None
    if "checkpoint_manager" not in st.session_state or st.session_state.checkpoint_manager is None:
        st.session_state.checkpoint_manager = CheckpointManager()
    return st.session_state.checkpoint_manager


def _get_gpu_status() -> str:
    """获取 GPU 状态字符串。"""
    if not _HAS_GPU_BACKEND:
        return "不可用"
    try:
        backend = detect_gpu()
        if backend.value == "NONE":
            return "未检测到"
        return backend.value
    except Exception:
        return "检测失败"


def _get_memory_status() -> dict:
    """获取内存状态字典。"""
    monitor = _get_performance_monitor()
    if monitor is None:
        return {"available": False, "message": "性能监控不可用"}
    try:
        return monitor.check_memory()
    except Exception as e:
        return {"available": False, "message": f"检测失败: {e}"}


def _get_performance_suggestions(image_path: Path | None = None) -> list[str]:
    """获取性能优化建议。"""
    monitor = _get_performance_monitor()
    if monitor is None or image_path is None:
        return []
    try:
        return monitor.suggest_optimization(str(image_path))
    except Exception:
        return []


def _save_workspace_state(name: str | None = None) -> None:
    """保存当前工作区状态。"""
    wm = _get_workspace_manager()
    if wm is None:
        st.session_state["ui_message"] = ("error", "工作区管理器不可用")
        return
    try:
        ws = Workspace(
            preset=st.session_state.get("preset_selector", "poster"),
            options=build_options_from_state(),
            uploaded_file_name=st.session_state.get("uploaded_file_name"),
        )
        path = wm.save(ws, name)
        st.session_state["ui_message"] = ("success", f"工作区已保存: {path.name}")
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"保存工作区失败: {e}")


def _load_workspace_state(name: str) -> None:
    """加载工作区状态。"""
    wm = _get_workspace_manager()
    if wm is None:
        st.session_state["ui_message"] = ("error", "工作区管理器不可用")
        return
    try:
        ws = wm.load(name)
        if ws.options:
            opts = ws.options
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
        if ws.preset:
            st.session_state.preset_selector = ws.preset
        st.session_state["ui_message"] = ("success", f"已加载工作区 '{name}'")
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"加载工作区失败: {e}")


def _check_crash_recovery() -> "Workspace | None":
    """检查是否有崩溃恢复数据。"""
    if not _HAS_WORKSPACE:
        return None
    try:
        return CrashRecovery.check_crash_recovery()
    except Exception:
        return None


def _list_workspaces() -> list[dict]:
    """列出所有工作区。"""
    wm = _get_workspace_manager()
    if wm is None:
        return []
    try:
        return wm.list_workspaces()
    except Exception:
        return []


def _list_checkpoints() -> list[dict]:
    """列出所有检查点。"""
    cm = _get_checkpoint_manager()
    if cm is None:
        return []
    try:
        return cm.list_checkpoints()
    except Exception:
        return []


def _save_checkpoint_for_batch(queue_id: str, tasks: list) -> None:
    """为批量队列保存检查点。"""
    cm = _get_checkpoint_manager()
    if cm is None:
        return
    try:
        cm.save_checkpoint(queue_id, tasks)
    except Exception:
        pass


def _get_tesseract_langs() -> list[str]:
    """获取已安装的 tesseract 语言包。"""
    if not _HAS_OCR_LANGUAGES:
        return []
    try:
        return get_tesseract_languages()
    except Exception:
        return []


# ---------------------------------------------------------------------------
# v1.2 Helpers
# ---------------------------------------------------------------------------

def _get_engine_registry() -> "EngineRegistry | None":
    """获取或初始化 EngineRegistry。"""
    if not _HAS_ENGINES:
        return None
    if "engine_registry" not in st.session_state or st.session_state.engine_registry is None:
        st.session_state.engine_registry = EngineRegistry()
    return st.session_state.engine_registry


def _list_engines() -> list[dict]:
    """列出所有可用引擎。"""
    registry = _get_engine_registry()
    if registry is None:
        return []
    try:
        return registry.list_engines()
    except Exception:
        return []


def _get_cloud_sync_manager() -> "CloudSyncManager | None":
    """获取或初始化 CloudSyncManager。"""
    if not _HAS_CLOUD_SYNC:
        return None
    if "cloud_sync_manager" not in st.session_state or st.session_state.cloud_sync_manager is None:
        st.session_state.cloud_sync_manager = CloudSyncManager()
    return st.session_state.cloud_sync_manager


def _share_svg(svg_path: Path) -> dict | None:
    """分享 SVG 到云端。"""
    manager = _get_cloud_sync_manager()
    if manager is None:
        return None
    try:
        return manager.share_svg(str(svg_path))
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"云端分享失败: {e}")
        return None


def _get_shared_files() -> list[dict]:
    """获取已分享文件列表。"""
    manager = _get_cloud_sync_manager()
    if manager is None:
        return []
    try:
        return manager.get_shared_files()
    except Exception:
        return []


def _auto_save_workspace() -> None:
    """自动保存工作区（每60秒）。"""
    if not _HAS_WORKSPACE:
        return
    now = time.time()
    last_auto_save = st.session_state.get("_last_auto_save", 0)
    if now - last_auto_save < 60:
        return
    try:
        wm = _get_workspace_manager()
        if wm is None:
            return
        ws = Workspace(
            preset=st.session_state.get("preset_selector", "poster"),
            options=build_options_from_state(),
            uploaded_file_name=st.session_state.get("uploaded_file_name"),
        )
        wm.save(ws, "auto_save")
        st.session_state["_last_auto_save"] = now
    except Exception:
        pass


# ---------------------------------------------------------------------------
# v2.0 Helpers
# ---------------------------------------------------------------------------

def _get_ai_processor() -> "AIProcessor | None":
    """获取或初始化 AIProcessor。"""
    if not _HAS_AI_ONNX:
        return None
    if "ai_processor" not in st.session_state or st.session_state.ai_processor is None:
        try:
            st.session_state.ai_processor = AIProcessor()
        except Exception:
            return None
    return st.session_state.ai_processor


def _get_engine_orchestrator() -> "EngineOrchestrator | None":
    """获取或初始化 EngineOrchestrator。"""
    if not _HAS_ENGINE_ORCHESTRATOR:
        return None
    if "engine_orchestrator" not in st.session_state or st.session_state.engine_orchestrator is None:
        try:
            st.session_state.engine_orchestrator = EngineOrchestrator()
        except Exception:
            return None
    return st.session_state.engine_orchestrator


def _get_collab_manager() -> "CollabManager | None":
    """获取或初始化 CollabManager。"""
    if not _HAS_COLLAB:
        return None
    if "collab_manager" not in st.session_state or st.session_state.collab_manager is None:
        try:
            st.session_state.collab_manager = CollabManager()
        except Exception:
            return None
    return st.session_state.collab_manager


def _get_animation_builder() -> "AnimationBuilder | None":
    """获取或初始化 AnimationBuilder。"""
    if not _HAS_ANIMATION:
        return None
    if "animation_builder" not in st.session_state or st.session_state.animation_builder is None:
        try:
            st.session_state.animation_builder = AnimationBuilder()
        except Exception:
            return None
    return st.session_state.animation_builder


def _get_sync_client() -> "SyncClient | None":
    """获取或初始化 SyncClient。"""
    if not _HAS_SYNC:
        return None
    if "sync_client" not in st.session_state or st.session_state.sync_client is None:
        try:
            st.session_state.sync_client = SyncClient()
        except Exception:
            return None
    return st.session_state.sync_client


def _list_workflow_templates() -> list[str]:
    """列出内置工作流模板。"""
    if not _HAS_WORKFLOW:
        return ["auto_enhance", "logo_pipeline", "photo_restore", "batch_optimize"]
    try:
        return Workflow.list_templates()
    except Exception:
        return ["auto_enhance", "logo_pipeline", "photo_restore", "batch_optimize"]


def _run_ai_task(image_path: Path, task: str, **kwargs) -> "Image.Image | None":
    """运行 AI 处理任务。"""
    processor = _get_ai_processor()
    if processor is None:
        return None
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            return processor.process(img, task=task, **kwargs)
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"AI 处理失败: {e}")
        return None


# ---------------------------------------------------------------------------
# Session state 初始化
# ---------------------------------------------------------------------------
if "initialized" not in st.session_state:
    apply_preset_values("poster")
    st.session_state.initialized = True
    st.session_state.smart_remove_bg = False
    st.session_state.enhance_enabled = False
    st.session_state.enhance_type = "auto"
    st.session_state.optimize_level = "basic"
    st.session_state.batch_running = False
    st.session_state.plugin_manager = None
    st.session_state.app_config = None
    st.session_state.api_process = None
    st.session_state.api_health = None
    # v0.5 live preview
    st.session_state.live_preview_enabled = False
    st.session_state.live_preview_engine = None
    st.session_state._preview_hash = ""
    st.session_state._preview_last_time = 0.0
    st.session_state._preview_bytes = None
    # v0.5 AI assist
    st.session_state.ai_simplify_enabled = False
    st.session_state.ai_simplify_type = "auto"
    st.session_state.ai_ocr_enabled = False
    st.session_state.ai_ocr_regions = None
    # v0.5 region trace
    st.session_state.region_x = 0
    st.session_state.region_y = 0
    st.session_state.region_w = 100
    st.session_state.region_h = 100
    st.session_state.region_result_svg = None
    # v0.5 market
    st.session_state.preset_market = None
    st.session_state.market_presets = None
    # v1.1 performance
    st.session_state.performance_monitor = None
    st.session_state.use_gpu = False
    st.session_state.streaming_process = False
    # v1.1 workspace
    st.session_state.workspace_manager = None
    st.session_state.checkpoint_manager = None
    st.session_state._last_auto_save = 0
    # v1.1 OCR
    st.session_state.ocr_language = "auto"
    st.session_state.ocr_vertical = False
    # v1.2 engines
    st.session_state.engine_selector = "自动选择"
    st.session_state.engine_benchmark_result = None
    # v1.2 plugin dev
    st.session_state.plugin_scaffold_name = ""
    st.session_state.plugin_validate_path = ""
    st.session_state.plugin_test_path = ""
    # v1.2 cloud sync
    st.session_state.cloud_share_result = None
    st.session_state.cloud_sync_manager = None
    # v2.0 AI ONNX
    st.session_state.ai_processor = None
    st.session_state.ai_task = "无"
    st.session_state.ai_style = "素描"
    st.session_state.ai_scale = 2
    st.session_state.ai_model_status = "未知"
    st.session_state.ai_result_image = None
    st.session_state.use_ai_result_for_trace = False
    # v2.0 engine orchestrator
    st.session_state.engine_orchestrator = None
    st.session_state.orchestrator_recommendation = None
    # v2.0 collaboration
    st.session_state.collab_manager = None
    st.session_state.collab_room_id = None
    st.session_state.collab_room_users = []
    # v2.0 animation
    st.session_state.animation_builder = None
    st.session_state.animation_preset = "绘制"
    st.session_state.animation_format = "SMIL"
    st.session_state.animation_result_path = None
    st.session_state.animation_result_bytes = None
    # v2.0 workflow
    st.session_state.workflow_engine = None
    st.session_state.workflow_template = "auto_enhance"
    st.session_state.workflow_result = None
    # v2.0 sync
    st.session_state.sync_client = None
    st.session_state.sync_server_url = "http://localhost:8000"

# ---------------------------------------------------------------------------
# 侧边栏
# ---------------------------------------------------------------------------
with st.sidebar:
    # 显示一次性的 toast 消息
    if "ui_message" in st.session_state:
        msg_type, msg_text = st.session_state.pop("ui_message")
        if msg_type == "success":
            st.success(msg_text)
        elif msg_type == "error":
            st.error(msg_text)
        elif msg_type == "warning":
            st.warning(msg_text)

    # -----------------------------------------------------------------------
    # v1.1: 工作区管理按钮组
    # -----------------------------------------------------------------------
    st.header("💾 工作区")
    ws_col1, ws_col2, ws_col3 = st.columns(3)
    with ws_col1:
        if st.button("保存", key="ws_save_btn"):
            _save_workspace_state()
            st.rerun()
    with ws_col2:
        workspaces = _list_workspaces()
        ws_names = [ws.get("name", "") for ws in workspaces if ws.get("name")]
        if ws_names:
            selected_ws = st.selectbox("加载", ws_names, key="ws_load_select", label_visibility="collapsed")
            if st.button("加载", key="ws_load_btn"):
                _load_workspace_state(selected_ws)
                st.rerun()
        else:
            st.caption("无工作区")
    with ws_col3:
        recovered = _check_crash_recovery()
        if recovered:
            if st.button("恢复上次", key="ws_recover_btn"):
                try:
                    wm = _get_workspace_manager()
                    if wm:
                        ws = wm.restore_last()
                        if ws and ws.options:
                            opts = ws.options
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
                        if ws and ws.preset:
                            st.session_state.preset_selector = ws.preset
                        st.session_state["ui_message"] = ("success", "已恢复上次会话")
                        st.rerun()
                except Exception as e:
                    st.session_state["ui_message"] = ("error", f"恢复失败: {e}")
                    st.rerun()
        else:
            st.caption("无恢复数据")

    st.divider()

    # -----------------------------------------------------------------------
    # v1.2: 引擎选择
    # -----------------------------------------------------------------------
    st.header("🔧 矢量化引擎")
    engine_options = ["自动选择", "VTracer", "Potrace", "AutoTrace"]
    if _HAS_ENGINES:
        engines = _list_engines()
        engine_status = {}
        for e in engines:
            name = e.get("name", "")
            available = e.get("available", False)
            engine_status[name] = available
        # Show availability
        status_lines = []
        for opt in engine_options:
            if opt == "自动选择":
                status_lines.append("• 自动选择: 根据图片类型智能选择")
            else:
                avail = engine_status.get(opt, False)
                status_lines.append(f"• {opt}: {'✅ 可用' if avail else '❌ 不可用'}")
        st.caption("\n".join(status_lines))

        st.selectbox("选择引擎", engine_options, key="engine_selector")

        if st.button("📊 引擎对比", key="engine_benchmark"):
            if uploaded is None:
                st.session_state["ui_message"] = ("warning", "请先上传图片再进行引擎对比")
            else:
                with st.spinner("正在对比引擎性能…"):
                    try:
                        with tempfile.TemporaryDirectory(prefix="vector-studio-benchmark-") as tmp:
                            tmp_dir = Path(tmp)
                            input_path = _save_uploaded_file(uploaded, tmp_dir)
                            result = EngineBenchmark.compare_engines(str(input_path))
                            st.session_state["engine_benchmark_result"] = result
                            st.session_state["ui_message"] = ("success", f"引擎对比完成，共 {len(result)} 个引擎")
                    except Exception as e:
                        st.session_state["ui_message"] = ("error", f"引擎对比失败: {e}")
                st.rerun()

        if st.session_state.get("engine_benchmark_result"):
            result = st.session_state["engine_benchmark_result"]
            with st.expander("对比结果"):
                for r in result:
                    name = r.get("engine", "-")
                    score = r.get("score", 0)
                    time_s = r.get("time_seconds", 0)
                    size_kb = r.get("size_kb", 0)
                    st.markdown(f"**{name}**: 评分 `{score:.1f}` | 耗时 `{time_s:.2f}s` | 大小 `{size_kb:.1f} KB`")
    else:
        st.warning("引擎管理模块不可用（vector_studio.engines 导入失败）")
        st.selectbox("选择引擎", engine_options, key="engine_selector", disabled=True)

    # -----------------------------------------------------------------------
    # v2.0: 智能编排
    # -----------------------------------------------------------------------
    if _HAS_ENGINE_ORCHESTRATOR:
        if st.button("🎼 智能编排", key="engine_orchestrate"):
            if "uploaded_file_name" not in st.session_state:
                st.session_state["ui_message"] = ("warning", "请先上传图片再进行智能编排")
            else:
                with st.spinner("正在分析图片并推荐最佳流水线…"):
                    try:
                        orchestrator = _get_engine_orchestrator()
                        if orchestrator is None:
                            st.session_state["ui_message"] = ("error", "编排器初始化失败")
                        else:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-orchestrate-") as tmp:
                                tmp_dir = Path(tmp)
                                input_path = _save_uploaded_file(uploaded, tmp_dir)
                                recs = orchestrator.recommend_pipeline(str(input_path))
                                st.session_state["orchestrator_recommendation"] = recs
                                st.session_state["ui_message"] = ("success", f"智能编排完成，推荐 {len(recs)} 个引擎")
                    except Exception as e:
                        st.session_state["ui_message"] = ("error", f"智能编排失败: {e}")
                st.rerun()

        if st.session_state.get("orchestrator_recommendation"):
            recs = st.session_state["orchestrator_recommendation"]
            with st.expander("推荐结果"):
                for r in recs:
                    engine_name = r.get("engine", "-") if isinstance(r, dict) else str(r)
                    reason = r.get("reason", "") if isinstance(r, dict) else ""
                    score = r.get("score", 0) if isinstance(r, dict) else 0
                    st.markdown(f"**{engine_name}**: {reason} (评分: {score})")
                if st.button("执行推荐流水线", key="run_recommended_pipeline"):
                    try:
                        with tempfile.TemporaryDirectory(prefix="vector-studio-pipeline-") as tmp:
                            tmp_dir = Path(tmp)
                            input_path = _save_uploaded_file(uploaded, tmp_dir)
                            out_path = tmp_dir / "pipeline_result.svg"
                            orchestrator = _get_engine_orchestrator()
                            if orchestrator:
                                result = orchestrator.run_pipeline(str(input_path), recs, str(out_path))
                                if result and hasattr(result, "svg_path") and result.svg_path:
                                    st.session_state["svg_text"] = result.svg_path.read_text(encoding="utf-8")
                                    st.session_state["svg_bytes"] = result.svg_path.read_bytes()
                                    st.session_state["stats"] = getattr(result, "stats", {})
                                    st.session_state["engine"] = getattr(result, "engine", "pipeline")
                                    st.session_state["elapsed"] = getattr(result, "elapsed_seconds", 0)
                                    st.session_state["ui_message"] = ("success", "推荐流水线执行完成")
                    except Exception as e:
                        st.session_state["ui_message"] = ("error", f"执行推荐流水线失败: {e}")
                    st.rerun()
    else:
        st.caption("🎼 智能编排不可用（vector_studio.engine_orchestrator 导入失败）")

    st.divider()

    # -----------------------------------------------------------------------
    # v2.0: AI 处理面板
    # -----------------------------------------------------------------------
    with st.expander("🤖 AI处理"):
        if not _HAS_AI_ONNX:
            st.warning("AI ONNX 模块不可用（vector_studio.ai_onnx 导入失败）")
        else:
            ai_task = st.selectbox(
                "AI任务",
                ["无", "分割", "风格迁移", "超分辨率", "自动增强"],
                key="ai_task",
            )

            # 显示模型下载状态
            try:
                manager = ONNXModelManager()
                models_ready = manager.list_ready_models()
                if models_ready:
                    st.caption(f"✅ 就绪模型: {', '.join(models_ready)}")
                else:
                    st.caption("⏳ 模型加载中…")
            except Exception:
                st.caption("模型状态检测不可用")

            if ai_task == "风格迁移":
                st.selectbox("风格", ["素描", "油画", "水彩", "卡通"], key="ai_style")
            elif ai_task == "超分辨率":
                st.selectbox("倍数", [2, 4], key="ai_scale", format_func=lambda x: f"{x}x")

            if ai_task != "无":
                if "uploaded_file_name" not in st.session_state:
                    st.caption("请先上传图片")
                elif st.button("运行 AI 处理", key="run_ai_task"):
                    with st.spinner(f"正在执行 {ai_task}…"):
                        try:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-ai-") as tmp:
                                tmp_dir = Path(tmp)
                                input_path = _save_uploaded_file(uploaded, tmp_dir)
                                kwargs = {}
                                if ai_task == "风格迁移":
                                    style_map = {"素描": "sketch", "油画": "oil", "水彩": "watercolor", "卡通": "cartoon"}
                                    kwargs["style"] = style_map.get(st.session_state.ai_style, "sketch")
                                elif ai_task == "超分辨率":
                                    kwargs["scale"] = st.session_state.ai_scale
                                result_img = _run_ai_task(input_path, ai_task, **kwargs)
                                if result_img is not None:
                                    out_path = tmp_dir / "ai_result.png"
                                    result_img.save(out_path)
                                    st.session_state["ai_result_image"] = out_path.read_bytes()
                                    st.session_state["ui_message"] = ("success", f"AI {ai_task} 完成")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"AI 处理失败: {e}")
                    st.rerun()

                if st.session_state.get("ai_result_image"):
                    st.image(st.session_state["ai_result_image"], caption="AI 处理结果", use_container_width=True)
                    if st.button("使用此结果进行矢量化", key="use_ai_result"):
                        st.session_state["use_ai_result_for_trace"] = True
                        st.session_state["ui_message"] = ("success", "已应用 AI 结果，请点击开始转换")
                        st.rerun()

    st.header("转换预设")

    preset_options = get_preset_options()
    current_preset = st.session_state.get("preset_selector", "poster")
    if current_preset not in preset_options:
        current_preset = "poster"
        apply_preset_values(current_preset)

    st.selectbox(
        "选择预设",
        preset_options,
        index=preset_options.index(current_preset) if current_preset in preset_options else 0,
        key="preset_selector",
        format_func=format_preset_name,
        on_change=on_preset_change,
    )

    # 保存当前参数为预设
    with st.expander("💾 保存当前参数为预设"):
        save_name = st.text_input("预设名称", key="save_preset_name")
        save_desc = st.text_input("描述（可选）", key="save_preset_desc")
        if st.button("保存", key="save_preset_button"):
            if not save_name.strip():
                st.warning("请输入预设名称")
            else:
                try:
                    if preset_exists(save_name):
                        st.error("该预设名称已存在（内置或用户预设）")
                    else:
                        opts = build_options_from_state()
                        save_preset(save_name, opts, save_desc)
                        st.session_state["ui_message"] = ("success", f"已保存预设 '{save_name}'")
                        st.rerun()
                except Exception as e:
                    st.session_state["ui_message"] = ("error", f"保存失败: {e}")
                    st.rerun()

    # 删除用户预设（仅对自定义预设显示）
    try:
        user_presets = list_user_presets()
    except Exception:
        user_presets = {}
    if st.session_state.preset_selector in user_presets:
        if st.button("🗑️ 删除此预设", key="delete_preset_button"):
            try:
                delete_preset(st.session_state.preset_selector)
                st.session_state["ui_message"] = ("success", f"已删除预设 '{st.session_state.preset_selector}'")
                apply_preset_values("poster")
                st.rerun()
            except Exception as e:
                st.session_state["ui_message"] = ("error", f"删除失败: {e}")
                st.rerun()

    st.divider()

    # -----------------------------------------------------------------------
    # v2.0: 工作流面板
    # -----------------------------------------------------------------------
    with st.expander("🔀 工作流"):
        if not _HAS_WORKFLOW:
            st.warning("工作流模块不可用（vector_studio.workflow 导入失败）")
        else:
            templates = _list_workflow_templates()
            st.selectbox("内置工作流模板", templates, key="workflow_template")
            if st.button("运行工作流", key="run_workflow"):
                if "uploaded_file_name" not in st.session_state:
                    st.session_state["ui_message"] = ("warning", "请先上传图片再运行工作流")
                else:
                    with st.spinner(f"正在运行工作流 '{st.session_state.workflow_template}'…"):
                        try:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-workflow-") as tmp:
                                tmp_dir = Path(tmp)
                                input_path = _save_uploaded_file(uploaded, tmp_dir)
                                wf = Workflow.load(st.session_state.workflow_template)
                                engine = WorkflowEngine()
                                result = engine.run_workflow(wf, {"image_path": str(input_path)})
                                st.session_state["workflow_result"] = result
                                st.session_state["ui_message"] = ("success", f"工作流 '{st.session_state.workflow_template}' 运行完成")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"工作流运行失败: {e}")
                    st.rerun()

            if st.session_state.get("workflow_result"):
                with st.expander("工作流结果"):
                    st.json(st.session_state["workflow_result"])

    st.divider()

    # 核心参数
    with st.expander("🎨 核心参数", expanded=True):
        st.radio("颜色模式", ["color", "binary"], key="colormode")
        st.radio("分层方式", ["stacked", "cutout"], key="hierarchical")
        st.radio("曲线拟合", ["spline", "polygon", "pixel", "none"], key="mode")

        slider_with_value("滤斑点 / Filter Speckle", 0, 128, "filter_speckle")
        slider_with_value("颜色精度 / Color Precision", 1, 8, "color_precision")
        slider_with_value("梯度层级间隔 / Layer Difference", 0, 255, "layer_difference")
        slider_with_value("角点阈值 / Corner Threshold", 0, 180, "corner_threshold")
        slider_with_value("曲线段长 / Length Threshold", 3.5, 10.0, "length_threshold", step=0.1)
        slider_with_value("拼接阈值 / Splice Threshold", 0, 180, "splice_threshold")
        slider_with_value("路径小数位 / Path Precision", 0, 12, "path_precision")

    with st.expander("🔧 高级参数"):
        slider_with_value("最大迭代次数 / Max Iterations", 1, 50, "max_iterations")

    with st.expander("🖼️ 预处理"):
        st.checkbox("轻度降噪", key="denoise")
        st.checkbox("🧠 智能背景透明", key="smart_remove_bg")
        st.checkbox("✨ 图像增强", key="enhance_enabled")
        st.selectbox("增强类型", ["auto", "scan", "photo", "logo"], key="enhance_type")
        # v0.5 AI assist
        if _HAS_AI_SIMPLIFY:
            st.checkbox("🤖 AI语义简化", key="ai_simplify_enabled")
            st.selectbox("简化类型", ["auto", "photo", "complex", "sketch"], key="ai_simplify_type")
        else:
            st.caption("🤖 AI语义简化不可用（vector_studio.ai_simplify 导入失败）")
        if _HAS_AI_OCR:
            st.checkbox("🔤 OCR文字识别", key="ai_ocr_enabled")
            # v1.1 OCR 多语言增强
            ocr_langs = ["auto", "eng", "chi_sim", "chi_tra", "jpn", "kor", "ara", "rus"]
            st.selectbox("OCR语言", ocr_langs, key="ocr_language")
            st.checkbox("检测竖排文字", key="ocr_vertical")
            installed_langs = _get_tesseract_langs()
            if installed_langs:
                st.caption(f"已安装语言包: {', '.join(installed_langs[:10])}{'...' if len(installed_langs) > 10 else ''}")
            else:
                st.caption("未检测到已安装的 tesseract 语言包")
        else:
            st.caption("🔤 OCR文字识别不可用（vector_studio.ai_ocr 导入失败）")
        st.checkbox("限制输入最大边长", key="max_input_side_enabled")
        st.number_input(
            "最大边长 px",
            min_value=64,
            max_value=10000,
            key="max_input_side",
            step=100,
            disabled=not st.session_state.max_input_side_enabled,
        )
        st.checkbox("先做颜色 Posterize", key="posterize_enabled")
        st.slider("Posterize bits", 1, 8, key="posterize", disabled=not st.session_state.posterize_enabled)

    with st.expander("📤 导出选项"):
        st.checkbox("启用 SVG 优化", value=True, key="optimize")
        st.radio(
            "SVG优化级别",
            ["basic", "comprehensive", "aggressive"],
            index=["basic", "comprehensive", "aggressive"].index(st.session_state.get("optimize_level", "basic")),
            key="optimize_level",
        )
        st.caption("basic = 清理空白 | comprehensive = 合并路径+颜色 | aggressive = 最大压缩")
        st.checkbox("同时导出 PDF", value=False, key="export_pdf")
        st.checkbox("同时导出 PNG 预览", value=False, key="export_png")

    st.divider()

    # -----------------------------------------------------------------------
    # v0.4: 插件管理面板
    # -----------------------------------------------------------------------
    with st.expander("🔌 插件管理"):
        if not _HAS_PLUGINS:
            st.warning("插件系统不可用（vector_studio.plugins 导入失败）")
        else:
            pm = _get_plugin_manager()
            if pm is None:
                st.error("插件管理器初始化失败")
            else:
                plugins = pm.list_plugins()
                if not plugins:
                    st.caption("未发现插件")
                else:
                    enabled_count = sum(1 for p in plugins if p.get("enabled"))
                    st.markdown(f"**已启用插件数:** `{enabled_count}` / `{len(plugins)}`")

                    for p in plugins:
                        name = p.get("name", "unknown")
                        version = p.get("version", "-")
                        description = p.get("description", "")
                        author = p.get("author", "")
                        enabled = p.get("enabled", False)
                        hooks = p.get("hooks", [])

                        col1, col2 = st.columns([4, 1])
                        with col1:
                            hook_badges = " ".join([f"`{h}`" for h in hooks]) if hooks else ""
                            st.markdown(
                                f"**{name}** `v{version}` {hook_badges}\n"
                                f"<small>{html.escape(description)} {html.escape(author)}</small>",
                                unsafe_allow_html=True,
                            )
                        with col2:
                            toggle_key = f"plugin_toggle_{name}"
                            # 使用 checkbox 作为切换按钮
                            was_enabled = enabled
                            is_now_enabled = st.checkbox(
                                "启用",
                                value=enabled,
                                key=toggle_key,
                                label_visibility="collapsed",
                            )
                            if is_now_enabled != was_enabled:
                                try:
                                    if is_now_enabled:
                                        pm.enable_plugin(name)
                                    else:
                                        pm.disable_plugin(name)
                                    st.session_state["ui_message"] = (
                                        "success",
                                        f"插件 '{name}' 已{'启用' if is_now_enabled else '禁用'}",
                                    )
                                    st.rerun()
                                except Exception as e:
                                    st.session_state["ui_message"] = ("error", f"插件切换失败: {e}")
                                    st.rerun()
                        st.divider()

                if st.button("🔄 重新扫描插件", key="rescan_plugins"):
                    with st.spinner("正在扫描插件…"):
                        try:
                            pm.discover_plugins()
                            st.session_state["ui_message"] = ("success", "插件扫描完成")
                            st.rerun()
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"扫描失败: {e}")
                            st.rerun()

        # -----------------------------------------------------------------------
        # v1.2: 插件开发工具
        # -----------------------------------------------------------------------
        if _HAS_PLUGIN_SDK:
            with st.expander("🛠️ 插件开发工具"):
                st.markdown("**生成插件模板**")
                scaffold_name = st.text_input("插件名称", key="plugin_scaffold_name_input", value=st.session_state.get("plugin_scaffold_name", ""))
                if st.button("生成模板", key="plugin_scaffold_btn"):
                    if not scaffold_name.strip():
                        st.warning("请输入插件名称")
                    else:
                        try:
                            from pathlib import Path as _Path
                            out_dir = _Path("plugins") / scaffold_name.strip()
                            out_dir.mkdir(parents=True, exist_ok=True)
                            path = PluginScaffold.generate(scaffold_name.strip(), str(out_dir))
                            st.session_state["ui_message"] = ("success", f"插件模板已生成: {path}")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"生成模板失败: {e}")
                        st.rerun()

                st.markdown("**验证插件**")
                validate_path = st.text_input("插件路径", key="plugin_validate_path_input", value=st.session_state.get("plugin_validate_path", ""))
                if st.button("验证", key="plugin_validate_btn"):
                    if not validate_path.strip():
                        st.warning("请输入插件路径")
                    else:
                        try:
                            ok, errors = PluginValidator.validate(validate_path.strip())
                            if ok:
                                st.session_state["ui_message"] = ("success", "插件验证通过")
                            else:
                                st.session_state["ui_message"] = ("error", f"验证失败: {'; '.join(errors)}")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"验证出错: {e}")
                        st.rerun()

                st.markdown("**测试插件**")
                test_path = st.text_input("插件路径", key="plugin_test_path_input", value=st.session_state.get("plugin_test_path", ""))
                if st.button("测试", key="plugin_test_btn"):
                    if not test_path.strip():
                        st.warning("请输入插件路径")
                    else:
                        try:
                            result = PluginDebugger.test_plugin(test_path.strip())
                            st.session_state["ui_message"] = ("success", f"测试结果: {result}")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"测试出错: {e}")
                        st.rerun()
        else:
            st.caption("🛠️ 插件开发工具不可用（vector_studio.plugin_sdk 导入失败）")

    # -----------------------------------------------------------------------
    # v0.4: 配置管理面板
    # -----------------------------------------------------------------------
    with st.expander("⚙️ 配置管理"):
        if not _HAS_CONFIG:
            st.warning("配置管理模块不可用（vector_studio.config 导入失败）")
        else:
            cfg = _get_config()
            if cfg is None:
                st.error("配置加载失败")
            else:
                st.markdown("**当前配置摘要**")
                out_dir = str(cfg.default_output_dir) if cfg.default_output_dir else "默认"
                st.markdown(
                    f"- 默认预设: `{cfg.default_preset}`\n"
                    f"- 优化级别: `{cfg.default_optimize_level}`\n"
                    f"- 输出目录: `{out_dir}`\n"
                    f"- 启用插件: `{', '.join(cfg.enabled_plugins) or '无'}`"
                )

                # 导出配置
                export_col1, export_col2 = st.columns(2)
                with export_col1:
                    cfg_json = json.dumps(cfg.to_dict(), indent=2, ensure_ascii=False)
                    st.download_button(
                        "导出 JSON",
                        data=cfg_json,
                        file_name="vector_studio_config.json",
                        mime="application/json",
                        key="export_config_json",
                    )
                with export_col2:
                    try:
                        import yaml

                        cfg_yaml = yaml.safe_dump(cfg.to_dict(), default_flow_style=False, allow_unicode=True, sort_keys=True)
                        st.download_button(
                            "导出 YAML",
                            data=cfg_yaml,
                            file_name="vector_studio_config.yaml",
                            mime="text/yaml",
                            key="export_config_yaml",
                        )
                    except Exception:
                        st.caption("YAML 导出不可用")

                # 导入配置
                st.markdown("---")
                uploaded_config = st.file_uploader(
                    "导入配置文件 (JSON/YAML)",
                    type=["json", "yaml", "yml"],
                    key="import_config_file",
                )
                if uploaded_config is not None:
                    if st.button("应用导入配置", key="apply_imported_config"):
                        try:
                            content = uploaded_config.read().decode("utf-8")
                            if uploaded_config.name.endswith((".yaml", ".yml")):
                                import yaml

                                data = yaml.safe_load(content)
                            else:
                                data = json.loads(content)
                            if not isinstance(data, dict):
                                raise ValueError("配置文件内容必须是字典")
                            new_cfg = Config.from_dict(data)
                            _save_config(new_cfg)
                            st.session_state["ui_message"] = ("success", "配置已导入并应用")
                            st.rerun()
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"导入配置失败: {e}")
                            st.rerun()

                # 重置配置
                st.markdown("---")
                if st.button("🔄 重置为默认配置", key="reset_config"):
                    try:
                        default_cfg = Config()
                        _save_config(default_cfg)
                        st.session_state["ui_message"] = ("success", "已重置为默认配置")
                        st.rerun()
                    except Exception as e:
                        st.session_state["ui_message"] = ("error", f"重置失败: {e}")
                        st.rerun()

                # -----------------------------------------------------------------------
                # v2.0: 跨设备同步
                # -----------------------------------------------------------------------
                st.markdown("---")
                st.markdown("**🔄 同步**")
                st.text_input("同步服务器 URL", key="sync_server_url", value=st.session_state.get("sync_server_url", "http://localhost:8000"))
                if st.button("同步工作区", key="sync_workspaces"):
                    if not _HAS_SYNC:
                        st.session_state["ui_message"] = ("error", "同步模块不可用")
                    else:
                        with st.spinner("正在同步…"):
                            try:
                                client = _get_sync_client()
                                if client:
                                    client.sync_workspaces()
                                    st.session_state["ui_message"] = ("success", "同步完成")
                                else:
                                    st.session_state["ui_message"] = ("error", "同步客户端初始化失败")
                            except Exception as e:
                                st.session_state["ui_message"] = ("error", f"同步失败: {e}")
                    st.rerun()

    # -----------------------------------------------------------------------
    # v0.4: API 服务面板
    # -----------------------------------------------------------------------
    with st.expander("🌐 API 服务"):
        if not _HAS_API_CLIENT:
            st.warning("API 客户端不可用（vector_studio.api_client 导入失败）")
        else:
            # 检查现有进程状态
            api_proc = st.session_state.get("api_process")
            health = _check_api_health()
            is_running = health is not None

            if is_running:
                st.success("API 服务运行中")
                st.markdown(f"- 端点: `http://localhost:8000`")
                st.markdown(f"- 状态: `{health.get('status', '-')}`")
                st.markdown(f"- 版本: `{health.get('version', '-')}`")
                st.markdown("- [API 文档](http://localhost:8000/docs)")
            else:
                st.info("API 服务未启动")

            ctrl1, ctrl2 = st.columns(2)
            with ctrl1:
                if st.button("▶️ 启动API服务", key="start_api"):
                    if is_running:
                        st.session_state["ui_message"] = ("warning", "API 服务已在运行")
                    else:
                        proc = _start_api_service()
                        if proc is None:
                            st.session_state["ui_message"] = ("error", "启动 API 服务失败")
                        else:
                            st.session_state.api_process = proc
                            st.session_state["ui_message"] = ("success", "API 服务已启动（端口 8000）")
                    st.rerun()
            with ctrl2:
                if st.button("⏹️ 停止API服务", key="stop_api"):
                    _stop_api_service(api_proc)
                    st.session_state.api_process = None
                    st.session_state["ui_message"] = ("success", "API 服务已停止")
                    st.rerun()

    st.divider()

    if st.button("↩️ 重置为当前预设默认值", key="reset_params"):
        apply_preset_values(st.session_state.preset_selector)
        st.session_state["ui_message"] = ("success", "已重置为当前预设默认值")
        st.rerun()

    # 历史记录面板
    with st.expander("🕐 最近任务"):
        try:
            tasks = get_recent_tasks(5)
        except Exception:
            tasks = []

        if not tasks:
            st.caption("暂无历史记录")
        else:
            for task in tasks:
                task_id = task.get("task_id", "")
                input_name = Path(task.get("input_path", "unknown")).name
                preset = task.get("preset_name", "-")
                elapsed = task.get("elapsed_seconds", 0)
                paths = task.get("stats", {}).get("paths", 0)

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(
                        f"<small>{html.escape(input_name)}<br>"
                        f"预设: {html.escape(preset)} | 耗时: {elapsed:.2f}s | 路径: {paths}</small>",
                        unsafe_allow_html=True,
                    )
                with col2:
                    if st.button("加载", key=f"load_task_{task_id}"):
                        try:
                            opts = get_task_options(task_id)
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

                            recorded_preset = task.get("preset_name", "")
                            if recorded_preset and recorded_preset in preset_options:
                                st.session_state.preset_selector = recorded_preset

                            st.session_state["ui_message"] = ("success", "已加载历史任务参数")
                            st.rerun()
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"加载失败: {e}")
                            st.rerun()
                st.divider()

        if st.button("清空历史", key="clear_history_button"):
            try:
                clear_history()
                st.session_state["ui_message"] = ("success", "历史记录已清空")
                st.rerun()
            except Exception as e:
                st.session_state["ui_message"] = ("error", f"清空失败: {e}")
                st.rerun()

    # -----------------------------------------------------------------------
    # v1.1: 性能面板
    # -----------------------------------------------------------------------
    with st.expander("⚡ 性能"):
        # 内存状态
        mem_status = _get_memory_status()
        if mem_status.get("available"):
            st.markdown(f"**内存使用:** `{mem_status.get('percent', '-'):.1f}%` ({mem_status.get('used_mb', '-')} MB / {mem_status.get('total_mb', '-')} MB)")
        else:
            st.caption(f"内存状态: {mem_status.get('message', '未知')}")

        # GPU 状态
        gpu_status = _get_gpu_status()
        st.markdown(f"**GPU 状态:** `{gpu_status}`")
        if _HAS_GPU_BACKEND and gpu_status != "未检测到":
            st.checkbox("使用 GPU 加速", key="use_gpu")
        else:
            st.caption("GPU 加速不可用")

        st.checkbox("流式处理大文件", key="streaming_process")

        # 性能建议
        if uploaded is not None:
            try:
                with tempfile.TemporaryDirectory(prefix="vector-studio-perf-") as tmp:
                    tmp_dir = Path(tmp)
                    input_path = _save_uploaded_file(uploaded, tmp_dir)
                    suggestions = _get_performance_suggestions(input_path)
                    if suggestions:
                        st.markdown("**优化建议:**")
                        for s in suggestions:
                            st.markdown(f"- {s}")
                    else:
                        st.caption("暂无优化建议")
            except Exception:
                st.caption("无法获取优化建议")
        else:
            st.caption("上传图片后显示优化建议")

    st.divider()
    st.caption("💡 每 60 秒自动保存工作区")


# ---------------------------------------------------------------------------
# 主区域
# ---------------------------------------------------------------------------

options = build_options_from_state()
optimize = st.session_state.get("optimize", True)
optimize_level = st.session_state.get("optimize_level", "basic") if optimize else "none"
export_pdf = st.session_state.get("export_pdf", False)
export_png = st.session_state.get("export_png", False)
smart_remove_bg = st.session_state.get("smart_remove_bg", False)
enhance_enabled = st.session_state.get("enhance_enabled", False)
enhance_type = st.session_state.get("enhance_type", "auto") if enhance_enabled else None

# -----------------------------------------------------------------------
# v2.0: 协作功能
# -----------------------------------------------------------------------
collab_col1, collab_col2, collab_col3 = st.columns([1, 1, 2])
with collab_col1:
    if st.button("👥 创建房间", key="create_collab_room"):
        if not _HAS_COLLAB:
            st.session_state["ui_message"] = ("error", "协作模块不可用")
        else:
            try:
                manager = _get_collab_manager()
                if manager:
                    room_id = manager.create_room("current_user")
                    st.session_state["collab_room_id"] = room_id
                    st.session_state["ui_message"] = ("success", f"协作房间已创建: {room_id}")
                else:
                    st.session_state["ui_message"] = ("error", "协作管理器初始化失败")
            except Exception as e:
                st.session_state["ui_message"] = ("error", f"创建房间失败: {e}")
        st.rerun()
with collab_col2:
    join_room_id = st.text_input("加入房间 ID", key="join_collab_room", placeholder="输入房间ID")
    if st.button("加入房间", key="join_collab_room_btn"):
        if not _HAS_COLLAB:
            st.session_state["ui_message"] = ("error", "协作模块不可用")
        else:
            try:
                manager = _get_collab_manager()
                if manager:
                    room = manager.get_room(join_room_id)
                    if room:
                        st.session_state["collab_room_id"] = join_room_id
                        st.session_state["ui_message"] = ("success", f"已加入房间: {join_room_id}")
                    else:
                        st.session_state["ui_message"] = ("warning", "房间不存在")
                else:
                    st.session_state["ui_message"] = ("error", "协作管理器初始化失败")
            except Exception as e:
                st.session_state["ui_message"] = ("error", f"加入房间失败: {e}")
        st.rerun()
with collab_col3:
    if st.session_state.get("collab_room_id"):
        st.markdown(f"**当前房间:** `{st.session_state['collab_room_id']}`")
        try:
            manager = _get_collab_manager()
            if manager:
                room = manager.get_room(st.session_state["collab_room_id"])
                users = room.get("users", []) if isinstance(room, dict) else []
                st.caption(f"在线用户: {', '.join(users) if users else '仅自己'}")
        except Exception:
            st.caption("在线用户: 获取失败")
    else:
        st.caption("未加入任何房间")

uploaded = st.file_uploader(
    "上传 PNG / JPG / WEBP / BMP / TIFF",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
)

# v1.1 自动保存工作区
_auto_save_workspace()

if uploaded is not None:
    st.session_state.uploaded_file_name = uploaded.name
    # 保存上传文件内容到 session_state 以便侧边栏 AI 面板使用
    st.session_state["uploaded_file_bytes"] = uploaded.getvalue()

    # v2.0: 如果使用 AI 结果进行矢量化，替换 input
    if st.session_state.get("use_ai_result_for_trace") and st.session_state.get("ai_result_image"):
        class _AIUploadedFile:
            name = "ai_result.png"
            file_id = "ai_result"
            type = "image/png"
            @staticmethod
            def getvalue():
                return st.session_state["ai_result_image"]
        uploaded = _AIUploadedFile()
        st.session_state["use_ai_result_for_trace"] = False

    # -----------------------------------------------------------------------
    # 1. 智能分析区域
    # -----------------------------------------------------------------------
    with st.container():
        if _HAS_SMART_RECOMMEND and st.button("🔍 智能分析", key="smart_analyze"):
            with st.spinner("正在分析图片特征…"):
                try:
                    with tempfile.TemporaryDirectory(prefix="vector-studio-analyze-") as tmp:
                        tmp_dir = Path(tmp)
                        input_path = _save_uploaded_file(uploaded, tmp_dir)
                        preset, confidence, reason, features = recommend_for_image(input_path)
                        st.session_state["smart_analysis_result"] = {
                            "preset": preset,
                            "confidence": confidence,
                            "reason": reason,
                            "features": features,
                        }
                except Exception as e:
                    st.session_state["ui_message"] = ("error", f"智能分析失败: {e}")
                    st.rerun()

        if "smart_analysis_result" in st.session_state:
            result = st.session_state["smart_analysis_result"]
            preset = result["preset"]
            confidence = result["confidence"]
            reason = result["reason"]
            features = result["features"]

            with st.container(border=True):
                st.markdown("#### 🔍 智能分析结果")
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"**推荐预设:** `{preset}`")
                    st.markdown(f"**置信度:** {confidence * 100:.0f}%")
                with c2:
                    st.markdown(f"**推荐理由:** {reason}")
                with c3:
                    if st.button("应用推荐", key="apply_recommend"):
                        if preset in preset_options:
                            apply_preset_values(preset)
                            st.session_state["ui_message"] = ("success", f"已应用推荐预设 '{preset}'")
                            st.rerun()
                        else:
                            st.warning(f"推荐预设 '{preset}' 不可用")

                with st.expander("图片特征摘要"):
                    fc1, fc2, fc3, fc4 = st.columns(4)
                    fc1.metric("分辨率", f"{features.get('width', 0)}×{features.get('height', 0)}")
                    fc2.metric("颜色数", features.get("color_count", "-"))
                    fc3.metric("边缘密度", features.get("edge_density", "-"))
                    fc4.metric("亮度均值", features.get("mean_brightness", "-"))

                    if features.get("is_likely_logo"):
                        st.info(f"🎯 检测到可能是 Logo: {features.get('logo_reason', '')}")

    # 当智能背景透明开启时，如果检测到可能是Logo，显示提示信息
    if smart_remove_bg and _HAS_SMART_BG:
        try:
            with tempfile.TemporaryDirectory(prefix="vector-studio-logo-check-") as tmp:
                tmp_dir = Path(tmp)
                input_path = _save_uploaded_file(uploaded, tmp_dir)
                from PIL import Image

                with Image.open(input_path) as img:
                    is_logo, logo_reason = is_likely_logo(img)
                if is_logo:
                    st.info(f"🧠 智能背景: 检测到 Logo 特征 ({logo_reason})，将自动移除背景")
        except Exception:
            pass

    preview_mode = st.radio("预览模式", ["并排对比", "叠加对比"], horizontal=True, key="preview_mode")

    # -----------------------------------------------------------------------
    # v0.5: 实时预览面板
    # -----------------------------------------------------------------------
    col_convert, col_preview_toggle = st.columns([1, 1])
    with col_convert:
        convert_clicked = st.button("开始转换", type="primary")
    with col_preview_toggle:
        st.checkbox("👁️ 实时预览", key="live_preview_enabled")

    if st.session_state.get("live_preview_enabled"):
        if not _HAS_LIVE_PREVIEW:
            st.warning("实时预览引擎不可用（vector_studio.live_preview 导入失败）")
        else:
            with st.container(border=True):
                st.caption("预览模式（低分辨率）")
                preview_cols = st.columns([3, 1])
                with preview_cols[0]:
                    if st.button("🔄 刷新预览", key="refresh_preview"):
                        st.session_state._preview_hash = ""
                with preview_cols[1]:
                    engine = _get_live_preview_engine()
                    if engine:
                        stats = engine.get_cache_stats()
                        st.caption(f"缓存: {stats['size']}/{stats['max_size']} | 命中率: {stats['hit_rate']*100:.0f}%")

                # 防抖：参数变化后至少间隔 0.5s 才重新生成
                current_hash = _hash_options(options)
                last_hash = st.session_state.get("_preview_hash", "")
                last_time = st.session_state.get("_preview_last_time", 0.0)
                now = time.time()

                preview_bytes = st.session_state.get("_preview_bytes")
                needs_refresh = False
                if current_hash != last_hash:
                    if now - last_time >= 0.5:
                        needs_refresh = True
                    else:
                        st.caption("⏳ 参数变化中，预览将在稳定后自动更新…")

                if needs_refresh or (preview_bytes is None and current_hash == last_hash):
                    with st.spinner("生成实时预览…"):
                        try:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-preview-ui-") as tmp:
                                tmp_dir = Path(tmp)
                                input_path = _save_uploaded_file(uploaded, tmp_dir)
                                preview_bytes = _run_live_preview(input_path, options)
                                if preview_bytes is not None:
                                    st.session_state._preview_bytes = preview_bytes
                                    st.session_state._preview_hash = current_hash
                                    st.session_state._preview_last_time = time.time()
                        except Exception as e:
                            st.warning(f"预览生成失败: {e}")

                preview_bytes = st.session_state.get("_preview_bytes")
                if preview_bytes:
                    svg_text = preview_bytes.decode("utf-8", errors="replace")
                    components.html(
                        f"""
                        <div style="width:100%;height:320px;overflow:auto;border:1px solid #ddd;background:white;display:flex;align-items:center;justify-content:center;">
                            {svg_text}
                        </div>
                        """,
                        height=340,
                        scrolling=True,
                    )
                else:
                    st.info("上传图片并调整参数后，实时预览将在此显示")

    # -----------------------------------------------------------------------
    # 转换流程（集成插件钩子 + AI 辅助）
    # -----------------------------------------------------------------------
    ai_simplify_enabled = st.session_state.get("ai_simplify_enabled", False) and _HAS_AI_SIMPLIFY
    ai_ocr_enabled = st.session_state.get("ai_ocr_enabled", False) and _HAS_AI_OCR
    simplify_type = st.session_state.get("ai_simplify_type", "auto") if ai_simplify_enabled else "auto"

    if convert_clicked:
        with st.spinner("正在转换 SVG…"):
            with tempfile.TemporaryDirectory(prefix="vector-studio-ui-") as tmp:
                tmp_dir = Path(tmp)
                input_path = _save_uploaded_file(uploaded, tmp_dir)
                svg_path = tmp_dir / "result.svg"

                # 准备插件实例
                plugin_instances = []
                if _HAS_PLUGINS:
                    try:
                        pm = _get_plugin_manager()
                        if pm is not None:
                            plugin_instances = pm.get_plugins()
                    except Exception as e:
                        st.warning(f"插件加载失败，将跳过插件处理: {e}")

                try:
                    result = trace_image(
                        input_path,
                        svg_path,
                        options,
                        optimize=optimize,
                        optimize_level=optimize_level,
                        export_pdf=export_pdf,
                        export_png=export_png,
                        smart_remove_bg=smart_remove_bg,
                        enhance=enhance_type,
                        plugins=plugin_instances,
                        ai_simplify=ai_simplify_enabled,
                        ai_ocr=ai_ocr_enabled,
                        simplify_type=simplify_type,
                    )
                    st.session_state["svg_text"] = result.svg_path.read_text(encoding="utf-8")
                    st.session_state["svg_bytes"] = result.svg_path.read_bytes()
                    st.session_state["stats"] = result.stats
                    st.session_state["engine"] = result.engine
                    st.session_state["elapsed"] = result.elapsed_seconds
                    st.session_state["pdf_bytes"] = result.pdf_path.read_bytes() if result.pdf_path else None
                    st.session_state["png_bytes"] = result.png_path.read_bytes() if result.png_path else None
                    st.session_state["last_preset_used"] = st.session_state.preset_selector
                    st.session_state["plugins_applied"] = len(plugin_instances) > 0
                    st.session_state["plugins_count"] = len(plugin_instances)
                    st.session_state["ai_ocr_regions"] = None

                    # AI OCR 结果收集
                    if ai_ocr_enabled and _HAS_AI_OCR:
                        try:
                            from PIL import Image
                            with Image.open(input_path) as img:
                                regions = recognize_text(img)
                                st.session_state["ai_ocr_regions"] = regions
                        except Exception:
                            pass

                    # SVG 质量评分
                    if _HAS_SVG_OPTIMIZER:
                        try:
                            scores = svg_quality_score(result.svg_path)
                            st.session_state["svg_quality"] = scores
                        except Exception:
                            st.session_state["svg_quality"] = None
                    else:
                        st.session_state["svg_quality"] = None

                    try:
                        record_task(result, st.session_state.preset_selector, options)
                    except Exception:
                        pass  # 历史记录失败不应阻断主流程

                    st.success("转换完成！")
                except Exception as e:
                    st.error(f"转换失败: {e}")

    if "svg_text" in st.session_state:
        if preview_mode == "并排对比":
            left, right = st.columns([1, 1])
            with left:
                st.subheader("原图")
                st.image(uploaded, use_container_width=True)
            with right:
                st.subheader("SVG 预览")
                components.html(
                    f"""
                    <div style="width:100%;height:620px;overflow:auto;border:1px solid #ddd;background:white;display:flex;align-items:center;justify-content:center;">
                        {st.session_state['svg_text']}
                    </div>
                    """,
                    height=650,
                    scrolling=True,
                )
        else:
            st.subheader("叠加对比（拖动滑块或点击画面查看差异）")
            orig_b64 = base64.b64encode(uploaded.getvalue()).decode()
            mime = uploaded.type or "image/png"
            svg_text = st.session_state["svg_text"]

            slider_html = f"""
            <div id="ba-slider" style="position:relative;width:100%;height:620px;overflow:hidden;background:#f5f5f5;border:1px solid #ddd;">
              <div style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;">
                <img src="data:{mime};base64,{orig_b64}" style="max-width:100%;max-height:100%;object-fit:contain;">
              </div>
              <div id="ba-overlay" style="position:absolute;top:0;left:0;width:100%;height:100%;display:flex;align-items:center;justify-content:center;clip-path:inset(0 50% 0 0);background:white;">
                <div class="svg-wrap" style="max-width:100%;max-height:100%;">{svg_text}</div>
              </div>
              <div id="ba-handle" style="position:absolute;top:0;left:50%;width:4px;height:100%;background:rgba(255,255,255,0.8);cursor:ew-resize;z-index:10;transform:translateX(-50%);box-shadow:0 0 4px rgba(0,0,0,0.2);">
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:40px;height:40px;background:white;border-radius:50%;display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.3);font-size:20px;color:#333;">⇄</div>
              </div>
            </div>
            <style>
              .svg-wrap svg {{ width: 100% !important; height: 100% !important; }}
            </style>
            <script>
            (function(){{
              const slider = document.getElementById('ba-slider');
              const overlay = document.getElementById('ba-overlay');
              const handle = document.getElementById('ba-handle');
              let dragging = false;
              function setPct(pct){{
                pct = Math.max(0, Math.min(100, pct));
                overlay.style.clipPath = 'inset(0 ' + (100-pct) + '% 0 0)';
                handle.style.left = pct + '%';
              }}
              handle.addEventListener('mousedown', function(e){{
                dragging = true;
                e.preventDefault();
              }});
              window.addEventListener('mouseup', function(){{
                dragging = false;
              }});
              window.addEventListener('mousemove', function(e){{
                if(!dragging) return;
                const rect = slider.getBoundingClientRect();
                setPct(((e.clientX - rect.left) / rect.width) * 100);
              }});
              slider.addEventListener('click', function(e){{
                if(e.target === handle || e.target.closest('#ba-handle')) return;
                const rect = slider.getBoundingClientRect();
                setPct(((e.clientX - rect.left) / rect.width) * 100);
              }});
            }})();
            </script>
            """
            components.html(slider_html, height=650, scrolling=False)

        # 结果统计
        st.subheader("结果")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Engine", st.session_state.get("engine", "-"))
        c2.metric("Time", f"{st.session_state.get('elapsed', 0):.2f}s")
        c3.metric("Paths", st.session_state.get("stats", {}).get("paths", 0))
        c4.metric("File size", f"{st.session_state.get('stats', {}).get('file_bytes', 0) / 1024:.1f} KB")

        # 插件处理提示
        if st.session_state.get("plugins_applied"):
            plugins_count = st.session_state.get("plugins_count", 0)
            st.info(f"🔌 插件已处理（{plugins_count} 个插件参与了转换流程）")

        # SVG 质量评分
        svg_quality = st.session_state.get("svg_quality")
        if svg_quality:
            st.subheader("质量评分")
            overall = svg_quality.get("overall", 0)
            color = _color_for_score(overall)
            st.markdown(f"{color} **综合评分:** `{overall:.0f}` / 100")
            with st.expander("各维度评分"):
                q1, q2, q3, q4 = st.columns(4)
                q1.metric("文件大小", svg_quality.get("file_size_score", 0))
                q2.metric("路径效率", svg_quality.get("path_efficiency", 0))
                q3.metric("复杂度", svg_quality.get("complexity_score", 0))
                q4.metric("颜色效率", svg_quality.get("color_efficiency", 0))

        # AI OCR 结果展示
        ocr_regions = st.session_state.get("ai_ocr_regions")
        if ocr_regions:
            with st.expander("🔤 OCR 文字识别结果"):
                if not ocr_regions:
                    st.caption("未检测到文字区域")
                else:
                    st.markdown(f"检测到 **{len(ocr_regions)}** 个文字区域：")
                    for i, region in enumerate(ocr_regions[:20], 1):
                        text = region.get("text", "")
                        bbox = region.get("bbox", [0, 0, 0, 0])
                        conf = region.get("confidence", 0)
                        st.markdown(
                            f"{i}. `{html.escape(text or '(未识别)')}` "
                            f"— 位置: {bbox} | 置信度: {conf*100:.0f}%"
                        )

        # SVG 结构
        with st.expander("📐 SVG 结构"):
            try:
                stats = st.session_state.get("stats", {})
                svg_text = st.session_state.get("svg_text", "")

                sc1, sc2, sc3, sc4 = st.columns(4)
                sc1.metric("路径数", stats.get("paths", 0))
                sc2.metric("多边形数", stats.get("polygons", 0))
                sc3.metric("矩形数", stats.get("rects", 0))
                sc4.metric("圆形数", stats.get("circles", 0))

                sg1, sg2 = st.columns(2)
                sg1.metric("组数", stats.get("groups", 0))
                sg2.metric("viewBox", stats.get("viewBox") or "-")

                file_bytes = stats.get("file_bytes", 0)
                st.metric("文件大小", f"{file_bytes / 1024:.1f} KB")

                layers = extract_svg_layers(svg_text)
                if layers:
                    st.markdown("**图层列表（按 `<g>` 元素）:**")
                    for i, layer in enumerate(layers, 1):
                        lid = layer.get("id", "-")
                        fill = layer.get("fill", "")
                        fill_badge = (
                            f'<span style="display:inline-block;width:12px;height:12px;background:{html.escape(fill)};'
                            f'border:1px solid #999;margin-right:4px;border-radius:2px;"></span>'
                            if fill else ""
                        )
                        st.markdown(f"{i}. {fill_badge} ID: `{html.escape(lid)}`", unsafe_allow_html=True)
            except Exception as e:
                st.warning(f"无法解析 SVG 结构: {e}")

        # 下载按钮
        dl_col1, dl_col2, dl_col3, dl_col4 = st.columns([1, 1, 1, 1])
        with dl_col1:
            st.download_button(
                "下载 SVG",
                data=st.session_state["svg_bytes"],
                file_name="vectorized.svg",
                mime="image/svg+xml",
            )
        with dl_col2:
            if st.session_state.get("pdf_bytes"):
                st.download_button("下载 PDF", data=st.session_state["pdf_bytes"], file_name="vectorized.pdf", mime="application/pdf")
        with dl_col3:
            if st.session_state.get("png_bytes"):
                st.download_button("下载 PNG 预览", data=st.session_state["png_bytes"], file_name="vectorized.png", mime="image/png")
        with dl_col4:
            if st.button("☁️ 云端分享", key="cloud_share_btn"):
                if not _HAS_CLOUD_SYNC:
                    st.session_state["ui_message"] = ("error", "云端同步模块不可用")
                else:
                    with st.spinner("正在上传到云端…"):
                        try:
                            with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="wb") as f:
                                f.write(st.session_state["svg_bytes"])
                                tmp_svg = Path(f.name)
                            result = _share_svg(tmp_svg)
                            if result:
                                st.session_state["cloud_share_result"] = result
                                st.session_state["ui_message"] = ("success", "云端分享成功")
                            else:
                                st.session_state["ui_message"] = ("error", "云端分享失败")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"分享失败: {e}")
                    st.rerun()

        # 云端分享结果
        if st.session_state.get("cloud_share_result"):
            share = st.session_state["cloud_share_result"]
            with st.container(border=True):
                st.subheader("☁️ 云端分享")
                url = share.get("url", "")
                qr_code = share.get("qr_code", "")
                if url:
                    st.markdown(f"**分享链接:** [{url}]({url})")
                if qr_code:
                    st.markdown("**QR 码:**")
                    st.markdown(
                        f'<img src="{qr_code}" style="max-width:200px;">',
                        unsafe_allow_html=True,
                    )
                if st.button("清除分享结果", key="clear_share_result"):
                    st.session_state["cloud_share_result"] = None
                    st.rerun()

        # 我的分享列表
        if _HAS_CLOUD_SYNC:
            with st.expander("📋 我的分享"):
                shared_files = _get_shared_files()
                if not shared_files:
                    st.caption("暂无分享文件")
                else:
                    st.markdown(f"**共 {len(shared_files)} 个分享文件**")
                    for sf in shared_files:
                        fname = sf.get("file_name", "-")
                        surl = sf.get("url", "")
                        created = sf.get("created_at", "-")
                        st.markdown(f"• `{fname}` — {created} — [{surl}]({surl})" if surl else f"• `{fname}` — {created}")

        # -----------------------------------------------------------------------
        # v2.0: 动画导出
        # -----------------------------------------------------------------------
        with st.expander("🎬 动画"):
            if not _HAS_ANIMATION:
                st.warning("动画模块不可用（vector_studio.animation 导入失败）")
            else:
                anim_col1, anim_col2 = st.columns(2)
                with anim_col1:
                    st.selectbox("动画预设", ["绘制", "揭示", "变形", "脉冲", "颜色循环"], key="animation_preset")
                with anim_col2:
                    st.selectbox("导出格式", ["SMIL", "Lottie", "GIF", "CSS"], key="animation_format")
                if st.button("生成动画", key="generate_animation"):
                    with st.spinner("正在生成动画…"):
                        try:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-anim-") as tmp:
                                tmp_dir = Path(tmp)
                                svg_path = tmp_dir / "input.svg"
                                svg_path.write_text(st.session_state["svg_text"], encoding="utf-8")
                                out_path = tmp_dir / f"animation.{st.session_state.animation_format.lower()}"
                                builder = _get_animation_builder()
                                if builder:
                                    builder.load_svg(str(svg_path)).apply_preset(
                                        st.session_state.animation_preset
                                    ).export(st.session_state.animation_format.lower(), str(out_path))
                                    st.session_state["animation_result_path"] = str(out_path)
                                    st.session_state["animation_result_bytes"] = out_path.read_bytes()
                                    st.session_state["ui_message"] = ("success", "动画生成完成")
                                else:
                                    st.session_state["ui_message"] = ("error", "动画构建器初始化失败")
                        except Exception as e:
                            st.session_state["ui_message"] = ("error", f"动画生成失败: {e}")
                    st.rerun()

                if st.session_state.get("animation_result_bytes"):
                    st.download_button(
                        f"下载 {st.session_state.animation_format}",
                        data=st.session_state["animation_result_bytes"],
                        file_name=f"animation.{st.session_state.animation_format.lower()}",
                        mime="application/json" if st.session_state.animation_format == "Lottie" else "text/plain",
                        key="download_animation",
                    )

        # 外部编辑器
        st.divider()
        st.subheader("外部编辑器")
        try:
            editors = detect_editors()
            available_editors = [e for e in editors if e.is_available]
        except Exception:
            available_editors = []

        if available_editors:
            editor_map = {e.display_name: e.name for e in available_editors}
            editor_options = ["系统默认"] + list(editor_map.keys())
            selected_editor = st.selectbox("选择编辑器", editor_options, key="editor_select")

            if st.button("用外部编辑器打开 SVG", key="open_editor"):
                try:
                    with tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="wb") as f:
                        f.write(st.session_state["svg_bytes"])
                        tmp_svg = Path(f.name)

                    if selected_editor == "系统默认":
                        open_with_editor(tmp_svg, None)
                    else:
                        open_with_editor(tmp_svg, editor_map[selected_editor])
                    st.success("已在外部编辑器中打开")
                except EditorNotFoundError:
                    st.warning("未找到指定的编辑器，请检查是否已安装")
                except EditorOpenError as e:
                    st.warning(f"打开失败: {e}")
                except Exception as e:
                    st.warning(f"打开出错: {e}")
        else:
            st.info("未检测到可用的外部矢量编辑器（如 Inkscape、Illustrator 等）")

    # -----------------------------------------------------------------------
    # 4. 参数搜索面板
    # -----------------------------------------------------------------------
    with st.expander("🎯 参数搜索"):
        if not _HAS_PARAM_SEARCH:
            st.warning("参数搜索模块不可用")
        else:
            search_mode = st.radio("搜索模式", ["快速搜索", "深度搜索"], horizontal=True, key="search_mode")

            if search_mode == "快速搜索":
                preset_candidates = st.multiselect(
                    "试跑预设",
                    list(BUILTIN_PRESET_NAMES),
                    default=["logo", "poster", "photo"],
                    key="quick_search_presets",
                )
                if st.button("开始快速搜索", key="run_quick_search"):
                    if not preset_candidates:
                        st.warning("请至少选择一个预设")
                    else:
                        with st.spinner("正在快速搜索最佳预设…"):
                            try:
                                with tempfile.TemporaryDirectory(prefix="vector-studio-search-") as tmp:
                                    tmp_dir = Path(tmp)
                                    input_path = _save_uploaded_file(uploaded, tmp_dir)
                                    out_dir = tmp_dir / "search"
                                    best_preset, best_path, best_score = quick_search(
                                        input_path, out_dir, preset_candidates=preset_candidates
                                    )
                                    st.session_state["quick_search_result"] = {
                                        "preset": best_preset,
                                        "path": best_path,
                                        "score": best_score,
                                    }
                                    st.success(f"最佳预设: {best_preset} (评分: {best_score:.1f})")
                            except Exception as e:
                                st.error(f"快速搜索失败: {e}")

                if "quick_search_result" in st.session_state:
                    res = st.session_state["quick_search_result"]
                    st.markdown(f"**最佳预设:** `{res['preset']}` | **评分:** `{res['score']:.1f}`")
                    if st.button("应用此预设", key="apply_quick_search"):
                        preset = res["preset"]
                        if preset in preset_options:
                            apply_preset_values(preset)
                            st.session_state["ui_message"] = ("success", f"已应用快速搜索结果 '{preset}'")
                            st.rerun()
                        else:
                            st.warning(f"预设 '{preset}' 不可用")

            else:
                st.markdown("**深度搜索参数范围**")
                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1:
                    cp_low = st.number_input("颜色精度下限", 1, 8, 4, key="deep_cp_low")
                    cp_high = st.number_input("颜色精度上限", 1, 8, 8, key="deep_cp_high")
                with dc2:
                    fs_low = st.number_input("滤斑点下限", 0, 128, 0, key="deep_fs_low")
                    fs_high = st.number_input("滤斑点上限", 0, 128, 8, key="deep_fs_high")
                with dc3:
                    ld_low = st.number_input("层级间隔下限", 0, 255, 8, key="deep_ld_low")
                    ld_high = st.number_input("层级间隔上限", 0, 255, 32, key="deep_ld_high")
                with dc4:
                    ct_low = st.number_input("角点阈值下限", 0, 180, 40, key="deep_ct_low")
                    ct_high = st.number_input("角点阈值上限", 0, 180, 80, key="deep_ct_high")

                deep_presets = st.multiselect(
                    "基础预设候选",
                    list(BUILTIN_PRESET_NAMES),
                    default=["logo", "poster", "photo"],
                    key="deep_search_presets",
                )
                max_combinations = st.slider("最多试跑组合数", 1, 50, 20, key="deep_max_combo")

                if st.button("开始深度搜索", key="run_deep_search"):
                    with st.spinner("正在深度搜索最佳参数…"):
                        try:
                            with tempfile.TemporaryDirectory(prefix="vector-studio-deep-") as tmp:
                                tmp_dir = Path(tmp)
                                input_path = _save_uploaded_file(uploaded, tmp_dir)
                                out_dir = tmp_dir / "search"
                                grid = ParamGrid(
                                    color_precision_range=(int(cp_low), int(cp_high)),
                                    filter_speckle_range=(int(fs_low), int(fs_high)),
                                    layer_difference_range=(int(ld_low), int(ld_high)),
                                    corner_threshold_range=(int(ct_low), int(ct_high)),
                                    preset_candidates=deep_presets or ["poster"],
                                )
                                best_options, best_path, best_score, all_results = search_best_params(
                                    input_path, out_dir, grid=grid, max_combinations=max_combinations
                                )
                                st.session_state["deep_search_result"] = {
                                    "options": best_options,
                                    "path": best_path,
                                    "score": best_score,
                                    "all_results": all_results,
                                }
                        except Exception as e:
                            st.error(f"深度搜索失败: {e}")

                if "deep_search_result" in st.session_state:
                    res = st.session_state["deep_search_result"]
                    best_options = res["options"]
                    best_score = res["score"]
                    all_results = res["all_results"]

                    st.markdown(f"**最佳评分:** `{best_score:.1f}`")
                    if st.button("应用此参数", key="apply_deep_search"):
                        st.session_state.colormode = best_options.colormode
                        st.session_state.hierarchical = best_options.hierarchical
                        st.session_state.mode = best_options.mode
                        st.session_state.filter_speckle = int(best_options.filter_speckle)
                        st.session_state.color_precision = int(best_options.color_precision)
                        st.session_state.layer_difference = int(best_options.layer_difference)
                        st.session_state.corner_threshold = int(best_options.corner_threshold)
                        st.session_state.length_threshold = float(best_options.length_threshold)
                        st.session_state.splice_threshold = int(best_options.splice_threshold)
                        st.session_state.path_precision = int(best_options.path_precision)
                        st.session_state.max_iterations = int(best_options.max_iterations)
                        st.session_state["ui_message"] = ("success", "已应用深度搜索最佳参数")
                        st.rerun()

                    with st.expander("搜索结果表格"):
                        table_data = []
                        for r in all_results:
                            opts = r["options"]
                            score = r["score"]
                            elapsed = r.get("elapsed", 0)
                            error = r.get("error", "")
                            try:
                                from vector_studio.svg_tools import svg_stats

                                stats = svg_stats(r["svg_path"])
                                file_bytes = stats.get("file_bytes", 0)
                                paths = stats.get("paths", 0)
                            except Exception:
                                file_bytes = 0
                                paths = 0
                            table_data.append(
                                {
                                    "预设": getattr(opts, "preset_name", "-"),
                                    "颜色精度": opts.color_precision,
                                    "滤斑点": opts.filter_speckle,
                                    "层级间隔": opts.layer_difference,
                                    "角点阈值": opts.corner_threshold,
                                    "文件大小(KB)": round(file_bytes / 1024, 1),
                                    "路径数": paths,
                                    "评分": round(score, 1) if score > float("-inf") else "失败",
                                    "耗时(s)": round(elapsed, 2),
                                    "错误": error[:30] if error else "",
                                }
                            )
                        st.dataframe(table_data, use_container_width=True)

    # -----------------------------------------------------------------------
    # 5. 批量队列面板
    # -----------------------------------------------------------------------
    with st.expander("📦 批量队列"):
        if not _HAS_TASK_QUEUE:
            st.warning("批量队列模块不可用")
        else:
            batch_files = st.file_uploader(
                "选择多个文件加入队列",
                type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
                accept_multiple_files=True,
                key="batch_uploader",
            )

            if batch_files:
                st.markdown(f"**已选择 {len(batch_files)} 个文件**")
                for f in batch_files:
                    st.caption(f"• {f.name}")

                if st.button("➕ 添加到队列", key="add_batch"):
                    try:
                        if "batch_queue" not in st.session_state or st.session_state.batch_queue is None:
                            st.session_state.batch_queue = TaskQueue(max_workers=4)
                        queue = st.session_state.batch_queue
                        task_ids = []
                        with tempfile.TemporaryDirectory(prefix="vector-studio-batch-") as tmp:
                            tmp_dir = Path(tmp)
                            for f in batch_files:
                                input_path = _save_uploaded_file(f, tmp_dir)
                                out_path = tmp_dir / f"{Path(f.name).stem}.svg"
                                tid = queue.add_task(
                                    input_path,
                                    out_path,
                                    build_options_from_state(),
                                    optimize_level=optimize_level,
                                )
                                task_ids.append(tid)
                        st.session_state.batch_task_ids = task_ids
                        # v1.1 自动保存检查点
                        _save_checkpoint_for_batch("batch_ui", task_ids)
                        st.session_state["ui_message"] = ("success", f"已添加 {len(task_ids)} 个任务到队列")
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加队列失败: {e}")

            # v1.1 断点续传
            with st.expander("🔄 断点续传"):
                checkpoints = _list_checkpoints()
                if checkpoints:
                    st.markdown(f"**可用检查点:** {len(checkpoints)} 个")
                    cp_names = [cp.get("name", cp.get("queue_id", "unknown")) for cp in checkpoints]
                    selected_cp = st.selectbox("选择检查点", cp_names, key="checkpoint_select")
                    if st.button("恢复检查点", key="resume_checkpoint_btn"):
                        try:
                            cm = _get_checkpoint_manager()
                            if cm:
                                tasks = cm.load_checkpoint(selected_cp)
                                if tasks:
                                    if "batch_queue" not in st.session_state or st.session_state.batch_queue is None:
                                        st.session_state.batch_queue = TaskQueue(max_workers=4)
                                    queue = st.session_state.batch_queue
                                    # 重新添加任务
                                    new_ids = []
                                    for task in tasks:
                                        tid = queue.add_task(
                                            task.input_path,
                                            task.output_path,
                                            task.options,
                                            optimize_level=optimize_level,
                                        )
                                        new_ids.append(tid)
                                    st.session_state.batch_task_ids = new_ids
                                    st.session_state["ui_message"] = ("success", f"已恢复 {len(new_ids)} 个任务")
                                    st.rerun()
                                else:
                                    st.warning("检查点中没有任务")
                        except Exception as e:
                            st.error(f"恢复检查点失败: {e}")
                else:
                    st.caption("暂无可用检查点")

            # 队列控制与状态显示
            queue = st.session_state.get("batch_queue")
            if queue is not None:
                st.divider()
                ctrl1, ctrl2, ctrl3 = st.columns(3)
                with ctrl1:
                    if st.button("▶️ 开始批量转换", key="batch_start"):
                        try:
                            queue.start()
                            st.session_state.batch_running = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"启动失败: {e}")
                with ctrl2:
                    if st.button("⏸️ 暂停", key="batch_pause"):
                        try:
                            queue.pause()
                            st.session_state["ui_message"] = ("warning", "队列已暂停")
                            st.rerun()
                        except Exception as e:
                            st.error(f"暂停失败: {e}")
                    if st.button("▶️ 恢复", key="batch_resume"):
                        try:
                            queue.resume()
                            st.session_state.batch_running = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"恢复失败: {e}")
                with ctrl3:
                    if st.button("⏹️ 取消全部", key="batch_cancel"):
                        try:
                            for tid in st.session_state.get("batch_task_ids", []):
                                queue.cancel(tid)
                            st.session_state.batch_running = False
                            st.session_state["ui_message"] = ("warning", "已取消所有任务")
                            st.rerun()
                        except Exception as e:
                            st.error(f"取消失败: {e}")

                # 状态表格
                statuses = queue.get_all_status()
                if statuses:
                    st.markdown("**任务列表**")
                    table_rows = []
                    for s in statuses:
                        table_rows.append(
                            {
                                "任务ID": s["task_id"][:8],
                                "文件": Path(s["input_path"]).name,
                                "状态": s["status"],
                                "进度": f"{s['progress']:.0f}%",
                                "输出": Path(s["output_path"]).name,
                            }
                        )
                    st.dataframe(table_rows, use_container_width=True)

                    # 自动刷新
                    if st.session_state.get("batch_running"):
                        all_done = all(
                            s["status"] in ("completed", "failed", "cancelled") for s in statuses
                        )
                        if not all_done:
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.session_state.batch_running = False
                            st.success("批量转换已完成")
                else:
                    st.caption("队列为空")

    # -----------------------------------------------------------------------
    # 6. 局部重描摹面板 (v0.5)
    # -----------------------------------------------------------------------
    with st.expander("✂️ 局部重描摹"):
        if not _HAS_REGION_TRACE:
            st.warning("局部重描摹模块不可用（vector_studio.region_trace 导入失败）")
        else:
            st.markdown("**选区设置**")
            rc1, rc2, rc3, rc4 = st.columns(4)
            with rc1:
                rx = st.number_input("X", min_value=0, value=st.session_state.region_x, key="region_x")
            with rc2:
                ry = st.number_input("Y", min_value=0, value=st.session_state.region_y, key="region_y")
            with rc3:
                rw = st.number_input("Width", min_value=1, value=st.session_state.region_w, key="region_w")
            with rc4:
                rh = st.number_input("Height", min_value=1, value=st.session_state.region_h, key="region_h")

            # 显示带选区框的原图
            try:
                from PIL import Image
                with tempfile.TemporaryDirectory(prefix="vector-studio-region-ui-") as tmp:
                    tmp_dir = Path(tmp)
                    input_path = _save_uploaded_file(uploaded, tmp_dir)
                    with Image.open(input_path) as img:
                        img_w, img_h = img.size
                        # Clamp region to image bounds for display
                        disp_x = min(rx, img_w)
                        disp_y = min(ry, img_h)
                        disp_w = min(rw, img_w - disp_x)
                        disp_h = min(rh, img_h - disp_y)
                    img_bytes = input_path.read_bytes()
                    mime = uploaded.type or "image/png"
                    st.components.v1.html(
                        _render_region_overlay(img_bytes, disp_x, disp_y, disp_w, disp_h, mime),
                        height=min(img_h, 400) + 20,
                    )
            except Exception as e:
                st.warning(f"无法渲染选区覆盖图: {e}")

            has_original_svg = "svg_text" in st.session_state
            merge_original = False
            if has_original_svg:
                merge_original = st.checkbox("合并到原图（使用当前 SVG 结果）", value=False, key="region_merge")

            if st.button("转换选区", key="region_trace_button"):
                with st.spinner("正在局部重描摹…"):
                    try:
                        with tempfile.TemporaryDirectory(prefix="vector-studio-region-run-") as tmp:
                            tmp_dir = Path(tmp)
                            input_path = _save_uploaded_file(uploaded, tmp_dir)
                            out_svg = tmp_dir / "region_result.svg"
                            region = RegionSelector(x=int(rx), y=int(ry), width=int(rw), height=int(rh), shape="rect")
                            original_svg_path = None
                            if merge_original and has_original_svg:
                                original_svg_path = tmp_dir / "original.svg"
                                original_svg_path.write_text(st.session_state["svg_text"], encoding="utf-8")
                            result = region_trace(
                                input_path,
                                region,
                                out_svg,
                                options,
                                original_svg=original_svg_path,
                            )
                            st.session_state["region_result_svg"] = result.svg_path.read_text(encoding="utf-8")
                            st.session_state["region_result_bytes"] = result.svg_path.read_bytes()
                            st.success("局部重描摹完成！")
                    except Exception as e:
                        st.error(f"局部重描摹失败: {e}")

            if st.session_state.get("region_result_svg"):
                st.subheader("局部结果预览")
                components.html(
                    f"""
                    <div style="width:100%;height:320px;overflow:auto;border:1px solid #ddd;background:white;display:flex;align-items:center;justify-content:center;">
                        {st.session_state['region_result_svg']}
                    </div>
                    """,
                    height=340,
                    scrolling=True,
                )
                st.download_button(
                    "下载局部 SVG",
                    data=st.session_state["region_result_bytes"],
                    file_name="region_vectorized.svg",
                    mime="image/svg+xml",
                    key="download_region_svg",
                )

    # -----------------------------------------------------------------------
    # 7. 预设市场浏览器 (v0.5)
    # -----------------------------------------------------------------------
    with st.expander("🏪 预设市场"):
        if not _HAS_MARKET:
            st.warning("预设市场模块不可用（vector_studio.market 导入失败）")
        else:
            market = _get_preset_market()
            if market is None:
                st.error("市场初始化失败")
            else:
                search_query = st.text_input("搜索预设", placeholder="输入关键词…", key="market_search_query")
                mc1, mc2 = st.columns([1, 1])
                with mc1:
                    if st.button("🔍 搜索", key="market_search_btn"):
                        with st.spinner("正在搜索…"):
                            try:
                                st.session_state["market_presets"] = market.search(search_query)
                            except Exception as e:
                                st.error(f"搜索失败: {e}")
                with mc2:
                    if st.button("🔄 刷新列表", key="market_refresh_btn"):
                        with st.spinner("正在获取市场列表…"):
                            try:
                                st.session_state["market_presets"] = market.discover_presets()
                            except Exception as e:
                                st.error(f"获取列表失败: {e}")

                # 热门预设快捷入口
                try:
                    popular = market.get_popular(limit=5)
                except Exception:
                    popular = []
                if popular:
                    st.markdown("**🔥 热门预设**")
                    pop_cols = st.columns(min(len(popular), 5))
                    for i, p in enumerate(popular):
                        with pop_cols[i]:
                            pid = p.get("id", "")
                            pname = p.get("display_name") or p.get("name", pid)
                            if st.button(f"{pname}", key=f"popular_{pid}"):
                                try:
                                    local_name = market.install(pid)
                                    st.session_state["ui_message"] = ("success", f"已安装热门预设 '{local_name}'")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"安装失败: {e}")

                presets = st.session_state.get("market_presets")
                if presets is not None:
                    if not presets:
                        st.caption("未找到预设（市场离线或搜索无结果）")
                    else:
                        st.markdown(f"**结果: {len(presets)} 个预设**")
                        for p in presets:
                            pid = p.get("id", "")
                            pname = p.get("display_name") or p.get("name", pid)
                            author = p.get("author", "-")
                            tags = ", ".join(p.get("tags", [])) or "-"
                            rating = p.get("rating", 0.0)
                            downloads = p.get("downloads", 0)

                            with st.container(border=True):
                                pc1, pc2 = st.columns([4, 1])
                                with pc1:
                                    st.markdown(
                                        f"**{html.escape(pname)}** `by {html.escape(author)}`\n"
                                        f"<small>标签: {html.escape(tags)} | ⭐ {rating} | ⬇️ {downloads}</small>",
                                        unsafe_allow_html=True,
                                    )
                                with pc2:
                                    if st.button("安装", key=f"install_{pid}"):
                                        try:
                                            local_name = market.install(pid)
                                            st.session_state["ui_message"] = ("success", f"已安装预设 '{local_name}'")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"安装失败: {e}")

else:
    st.info("上传图片后，可以先用 `poster` 或 `logo` 预设；照片素材再切到 `photo` 。")
