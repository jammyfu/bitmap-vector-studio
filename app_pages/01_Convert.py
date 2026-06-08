"""核心转换页面 — 三步流程：上传 → 调整 → 转换."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from app_pages._shared import (
    apply_preset_values,
    build_options_from_state,
    color_for_score,
    format_preset_name,
    get_preset_options,
    record_task,
    show_ui_message,
    trace_image,
    _HAS_AI_OCR,
    _HAS_AI_SIMPLIFY,
    _HAS_ENHANCE,
    _HAS_SMART_BG,
    _HAS_SMART_RECOMMEND,
    _HAS_SVG_OPTIMIZER,
)

if _HAS_SMART_RECOMMEND:
    from vector_studio.smart_recommend import recommend_for_image

if _HAS_SMART_BG:
    from vector_studio.smart_background import is_likely_logo


st.title("🎨 Bitmap Vector Studio")
st.caption("位图转矢量工具 — 上传、调整、转换")

show_ui_message()

# ---------------------------------------------------------------------------
# 1. 上传
# ---------------------------------------------------------------------------
st.markdown("### 1. 上传图片")

uploaded = st.file_uploader(
    "拖拽图片到此处或点击选择文件",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
    accept_multiple_files=False,
    label_visibility="collapsed",
)

if uploaded is not None:
    st.session_state.uploaded_file_bytes = uploaded.getvalue()
    st.session_state.uploaded_file_name = uploaded.name
    st.session_state.uploaded_file_type = uploaded.type or "image/png"

has_upload = bool(st.session_state.get("uploaded_file_bytes"))

if has_upload:
    st.info(f"当前文件: **{st.session_state.uploaded_file_name}**")

    # 智能推荐（自动触发一次）
    if _HAS_SMART_RECOMMEND and "smart_analysis_result" not in st.session_state:
        with st.spinner("正在智能分析图片…"):
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_dir = Path(tmp)
                    input_path = tmp_dir / st.session_state.uploaded_file_name
                    input_path.write_bytes(st.session_state.uploaded_file_bytes)
                    preset, confidence, reason, features = recommend_for_image(input_path)
                    st.session_state.smart_analysis_result = {
                        "preset": preset,
                        "confidence": confidence,
                        "reason": reason,
                        "features": features,
                    }
            except Exception as e:
                st.session_state["ui_message"] = ("warning", f"智能分析失败: {e}")

    if "smart_analysis_result" in st.session_state:
        result = st.session_state.smart_analysis_result
        preset = result["preset"]
        confidence = result["confidence"]
        reason = result["reason"]
        rc1, rc2 = st.columns([3, 1])
        with rc1:
            st.markdown(
                f"🤖 智能推荐: **{preset}** 预设 ({confidence * 100:.0f}%) — {reason}"
            )
        with rc2:
            if st.button("应用推荐", key="apply_recommend"):
                if preset in get_preset_options():
                    apply_preset_values(preset)
                    st.session_state["ui_message"] = ("success", f"已应用推荐预设 '{preset}'")
                    st.rerun()
                else:
                    st.session_state["ui_message"] = ("warning", f"推荐预设 '{preset}' 不可用")
                    st.rerun()

    # Logo 背景移除提示
    if st.session_state.get("smart_remove_bg") and _HAS_SMART_BG:
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                input_path = tmp_dir / st.session_state.uploaded_file_name
                input_path.write_bytes(st.session_state.uploaded_file_bytes)
                from PIL import Image
                with Image.open(input_path) as img:
                    is_logo, logo_reason = is_likely_logo(img)
                if is_logo:
                    st.info(f"🧠 检测到 Logo 特征 ({logo_reason})，将自动移除背景")
        except Exception:
            pass
    # -----------------------------------------------------------------------
    # 2. 调整参数
    # -----------------------------------------------------------------------
    st.markdown("### 2. 调整参数")
    preset_options = get_preset_options()
    current_preset = st.session_state.get("preset_selector", "poster")
    if current_preset not in preset_options:
        current_preset = "poster"
        apply_preset_values(current_preset)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(
            "预设",
            preset_options,
            index=preset_options.index(current_preset),
            key="preset_selector",
            format_func=format_preset_name,
            on_change=lambda: apply_preset_values(st.session_state.preset_selector),
        )
    with c2:
        st.selectbox("颜色模式", ["color", "binary"], key="colormode")
    with c3:
        st.selectbox("曲线模式", ["spline", "polygon", "pixel", "none"], key="mode")
    st.markdown("**优化级别**")
    st.radio(
        "optimize_level",
        options=["basic", "comprehensive", "aggressive"],
        format_func=lambda x: {"basic": "基础", "comprehensive": "综合", "aggressive": "激进"}.get(x, x),
        key="optimize_level",
        horizontal=True,
        label_visibility="collapsed",
    )
    # 高级参数（折叠）
    with st.expander("▼ 高级参数", expanded=False):
        a1, a2 = st.columns(2)
        with a1:
            st.number_input("滤斑点", 0, 128, key="filter_speckle")
            st.number_input("颜色精度", 1, 8, key="color_precision")
            st.number_input("层级间隔", 0, 255, key="layer_difference")
            st.number_input("角点阈值", 0, 180, key="corner_threshold")
        with a2:
            st.number_input("曲线段长", 3.5, 10.0, key="length_threshold", step=0.1)
            st.number_input("拼接阈值", 0, 180, key="splice_threshold")
            st.number_input("路径精度", 0, 12, key="path_precision")
            st.number_input("最大迭代", 1, 50, key="max_iterations")
        st.checkbox("轻度降噪", key="denoise")
        st.checkbox("🧠 智能背景透明", key="smart_remove_bg")
        st.checkbox("✨ 图像增强", key="enhance_enabled")
        if st.session_state.enhance_enabled:
            st.selectbox("增强类型", ["auto", "scan", "photo", "logo"], key="enhance_type")
        if _HAS_AI_SIMPLIFY:
            st.checkbox("🤖 AI语义简化", key="ai_simplify_enabled")
            if st.session_state.ai_simplify_enabled:
                st.selectbox("简化类型", ["auto", "photo", "complex", "sketch"], key="ai_simplify_type")
        if _HAS_AI_OCR:
            st.checkbox("🔤 OCR文字识别", key="ai_ocr_enabled")
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
    # -----------------------------------------------------------------------
    # 3. 开始转换
    # -----------------------------------------------------------------------
    st.markdown("### 3. 开始转换")
    convert_clicked = st.button(
        "▶ 开始转换", type="primary", use_container_width=True, disabled=not has_upload
    )
    if convert_clicked:
        with st.spinner("正在转换 SVG…"):
            with tempfile.TemporaryDirectory() as tmp:
                tmp_dir = Path(tmp)
                input_path = tmp_dir / st.session_state.uploaded_file_name
                input_path.write_bytes(st.session_state.uploaded_file_bytes)
                svg_path = tmp_dir / "result.svg"
                options = build_options_from_state()
                optimize_level = st.session_state.get("optimize_level", "basic")
                smart_remove_bg = st.session_state.get("smart_remove_bg", False)
                enhance_type = (
                    st.session_state.get("enhance_type", "auto")
                    if st.session_state.get("enhance_enabled")
                    else None
                )
                ai_simplify = st.session_state.get("ai_simplify_enabled", False) and _HAS_AI_SIMPLIFY
                ai_ocr = st.session_state.get("ai_ocr_enabled", False) and _HAS_AI_OCR
                try:
                    result = trace_image(
                        input_path,
                        svg_path,
                        options,
                        optimize=True,
                        optimize_level=optimize_level,
                        smart_remove_bg=smart_remove_bg,
                        enhance=enhance_type,
                        ai_simplify=ai_simplify,
                        ai_ocr=ai_ocr,
                        simplify_type=st.session_state.get("ai_simplify_type", "auto"),
                    )
                    st.session_state["svg_text"] = result.svg_path.read_text(encoding="utf-8")
                    st.session_state["svg_bytes"] = result.svg_path.read_bytes()
                    st.session_state["stats"] = result.stats
                    st.session_state["engine"] = result.engine
                    st.session_state["elapsed"] = result.elapsed_seconds
                    st.session_state["last_preset_used"] = st.session_state.preset_selector
                    if _HAS_SVG_OPTIMIZER:
                        try:
                            from vector_studio.svg_optimizer import svg_quality_score
                            scores = svg_quality_score(result.svg_path)
                            st.session_state["svg_quality"] = scores
                        except Exception:
                            st.session_state["svg_quality"] = None
                    try:
                        record_task(result, st.session_state.preset_selector, options)
                    except Exception:
                        pass
                    st.session_state["ui_message"] = ("success", "转换完成！")
                    st.rerun()
                except Exception as e:
                    st.session_state["ui_message"] = ("error", f"转换失败: {e}")
                    st.rerun()
    # -----------------------------------------------------------------------
    # 结果展示
    # -----------------------------------------------------------------------
    if "svg_text" in st.session_state:
        st.divider()
        st.markdown("### 📊 转换结果")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("引擎", st.session_state.get("engine", "-"))
        s2.metric("耗时", f"{st.session_state.get('elapsed', 0):.2f}s")
        s3.metric("路径数", st.session_state.get("stats", {}).get("paths", 0))
        s4.metric(
            "文件大小",
            f"{st.session_state.get('stats', {}).get('file_bytes', 0) / 1024:.1f} KB",
        )
        svg_quality = st.session_state.get("svg_quality")
        if svg_quality:
            overall = svg_quality.get("overall", 0)
            st.markdown(f"{color_for_score(overall)} **SVG 质量评分:** `{overall:.0f}` / 100")
        st.download_button(
            "⬇ 下载 SVG",
            data=st.session_state["svg_bytes"],
            file_name="vectorized.svg",
            mime="image/svg+xml",
            use_container_width=True,
        )
        with st.expander("▼ SVG 预览", expanded=True):
            components.html(
                f"""
                <div style="width:100%;height:500px;overflow:auto;border:1px solid #ddd;
                            background:white;display:flex;align-items:center;justify-content:center;">
                    {st.session_state['svg_text']}
                </div>
                """,
                height=520,
                scrolling=True,
            )
        if st.button("🗑 清除结果", key="clear_result"):
            for key in [
                "svg_text",
                "svg_bytes",
                "stats",
                "engine",
                "elapsed",
                "svg_quality",
                "last_preset_used",
            ]:
                st.session_state.pop(key, None)
            st.rerun()
else:
    st.info("请上传图片开始转换。支持 PNG、JPG、WEBP、BMP、TIFF 格式。")
