from __future__ import annotations

import tempfile
from dataclasses import replace
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from vector_studio.presets import PRESETS, options_from_preset
from vector_studio.svg_tools import export_svg_to_pdf, export_svg_to_png
from vector_studio.tracer import trace_image

st.set_page_config(page_title="Bitmap Vector Studio", page_icon="🖋️", layout="wide")
st.title("Bitmap Vector Studio")
st.caption("VTracer 驱动的 Illustrator-like 位图转 SVG 工具")

with st.sidebar:
    st.header("转换预设")
    preset_name = st.selectbox("Preset", list(PRESETS.keys()), index=list(PRESETS.keys()).index("poster"))
    base = options_from_preset(preset_name)

    st.header("核心参数")
    colormode = st.radio("颜色模式", ["color", "binary"], index=0 if base.colormode == "color" else 1)
    hierarchical = st.radio("分层方式", ["stacked", "cutout"], index=0 if base.hierarchical == "stacked" else 1)
    mode = st.radio("曲线拟合", ["spline", "polygon", "pixel", "none"], index=["spline", "polygon", "pixel", "none"].index(base.mode))

    filter_speckle = st.slider("Filter Speckle / 滤斑点", 0, 128, base.filter_speckle)
    color_precision = st.slider("Color Precision / 颜色精度", 1, 8, base.color_precision)
    layer_difference = st.slider("Layer Difference / 梯度层级间隔", 0, 255, base.layer_difference)
    corner_threshold = st.slider("Corner Threshold / 角点阈值", 0, 180, base.corner_threshold)
    length_threshold = st.slider("Length Threshold / 曲线段长", 3.5, 10.0, float(base.length_threshold), 0.1)
    splice_threshold = st.slider("Splice Threshold / 拼接阈值", 0, 180, base.splice_threshold)
    path_precision = st.slider("Path Precision / 路径小数位", 0, 12, base.path_precision)

    st.header("预处理")
    denoise = st.checkbox("轻度降噪", value=base.denoise)
    max_input_side_enabled = st.checkbox("限制输入最大边长", value=base.max_input_side is not None)
    max_input_side = st.number_input(
        "最大边长 px",
        min_value=64,
        max_value=10000,
        value=int(base.max_input_side or 2400),
        step=100,
        disabled=not max_input_side_enabled,
    )
    posterize_enabled = st.checkbox("先做颜色 Posterize", value=base.posterize is not None)
    posterize = st.slider("Posterize bits", 1, 8, int(base.posterize or 6), disabled=not posterize_enabled)

    st.header("导出")
    optimize = st.checkbox("压缩清理 SVG", value=True)
    export_pdf = st.checkbox("同时导出 PDF", value=False)
    export_png = st.checkbox("同时导出 PNG 预览", value=False)

uploaded = st.file_uploader("上传 PNG / JPG / WEBP / BMP / TIFF", type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"])

options = replace(
    base,
    colormode=colormode,
    hierarchical=hierarchical,
    mode=mode,
    filter_speckle=filter_speckle,
    color_precision=color_precision,
    layer_difference=layer_difference,
    corner_threshold=corner_threshold,
    length_threshold=length_threshold,
    splice_threshold=splice_threshold,
    path_precision=path_precision,
    denoise=denoise,
    max_input_side=int(max_input_side) if max_input_side_enabled else None,
    posterize=int(posterize) if posterize_enabled else None,
).validate()

left, right = st.columns([1, 1])

if uploaded is not None:
    with left:
        st.subheader("原图")
        st.image(uploaded, use_container_width=True)

    suffix = Path(uploaded.name).suffix or ".png"
    if st.button("开始转换", type="primary"):
        with st.spinner("正在转换 SVG…"):
            with tempfile.TemporaryDirectory(prefix="vector-studio-ui-") as tmp:
                tmp_dir = Path(tmp)
                input_path = tmp_dir / f"input{suffix}"
                svg_path = tmp_dir / "result.svg"
                input_path.write_bytes(uploaded.getvalue())
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

if "svg_text" in st.session_state:
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

    st.subheader("结果")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Engine", st.session_state.get("engine", "-"))
    c2.metric("Time", f"{st.session_state.get('elapsed', 0):.2f}s")
    c3.metric("Paths", st.session_state.get("stats", {}).get("paths", 0))
    c4.metric("File size", f"{st.session_state.get('stats', {}).get('file_bytes', 0) / 1024:.1f} KB")

    st.download_button(
        "下载 SVG",
        data=st.session_state["svg_bytes"],
        file_name="vectorized.svg",
        mime="image/svg+xml",
    )
    if st.session_state.get("pdf_bytes"):
        st.download_button("下载 PDF", data=st.session_state["pdf_bytes"], file_name="vectorized.pdf", mime="application/pdf")
    if st.session_state.get("png_bytes"):
        st.download_button("下载 PNG 预览", data=st.session_state["png_bytes"], file_name="vectorized.png", mime="image/png")
else:
    st.info("上传图片后，可以先用 `poster` 或 `logo` 预设；照片素材再切到 `photo`。")
