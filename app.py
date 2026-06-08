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

uploaded = st.file_uploader(
    "上传 PNG / JPG / WEBP / BMP / TIFF",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
)

if uploaded is not None:
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
        dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 2])
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
                        st.session_state["ui_message"] = ("success", f"已添加 {len(task_ids)} 个任务到队列")
                        st.rerun()
                    except Exception as e:
                        st.error(f"添加队列失败: {e}")

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
