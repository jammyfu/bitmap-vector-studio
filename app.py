from __future__ import annotations

import base64
import html
import tempfile
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


# ---------------------------------------------------------------------------
# Session state 初始化
# ---------------------------------------------------------------------------
if "initialized" not in st.session_state:
    apply_preset_values("poster")
    st.session_state.initialized = True

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
        st.checkbox("压缩清理 SVG", value=True, key="optimize")
        st.checkbox("同时导出 PDF", value=False, key="export_pdf")
        st.checkbox("同时导出 PNG 预览", value=False, key="export_png")

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
export_pdf = st.session_state.get("export_pdf", False)
export_png = st.session_state.get("export_png", False)

uploaded = st.file_uploader("上传 PNG / JPG / WEBP / BMP / TIFF", type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"])

if uploaded is not None:
    preview_mode = st.radio("预览模式", ["并排对比", "叠加对比"], horizontal=True, key="preview_mode")

    if st.button("开始转换", type="primary"):
        with st.spinner("正在转换 SVG…"):
            with tempfile.TemporaryDirectory(prefix="vector-studio-ui-") as tmp:
                tmp_dir = Path(tmp)
                suffix = Path(uploaded.name).suffix or ".png"
                input_path = tmp_dir / f"input{suffix}"
                svg_path = tmp_dir / "result.svg"
                input_path.write_bytes(uploaded.getvalue())

                try:
                    result = trace_image(
                        input_path,
                        svg_path,
                        options,
                        optimize=optimize,
                        export_pdf=export_pdf,
                        export_png=export_png,
                    )
                    st.session_state["svg_text"] = result.svg_path.read_text(encoding="utf-8")
                    st.session_state["svg_bytes"] = result.svg_path.read_bytes()
                    st.session_state["stats"] = result.stats
                    st.session_state["engine"] = result.engine
                    st.session_state["elapsed"] = result.elapsed_seconds
                    st.session_state["pdf_bytes"] = result.pdf_path.read_bytes() if result.pdf_path else None
                    st.session_state["png_bytes"] = result.png_path.read_bytes() if result.png_path else None
                    st.session_state["last_preset_used"] = st.session_state.preset_selector

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
else:
    st.info("上传图片后，可以先用 `poster` 或 `logo` 预设；照片素材再切到 `photo` 。")
