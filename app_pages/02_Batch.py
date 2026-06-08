"""批量转换页面 — 多文件队列与进度展示."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from app_pages._shared import (
    apply_preset_values,
    build_options_from_state,
    format_preset_name,
    get_preset_options,
    record_task,
    show_ui_message,
    trace_image,
)

st.title("📁 批量转换")
st.caption("一次性转换多张图片")

show_ui_message()

# Preset selector
preset_options = get_preset_options()
current_preset = st.session_state.get("preset_selector", "poster")
if current_preset not in preset_options:
    current_preset = "poster"

st.selectbox(
    "预设",
    preset_options,
    index=preset_options.index(current_preset),
    key="batch_preset",
    format_func=format_preset_name,
    on_change=lambda: apply_preset_values(st.session_state.batch_preset),
)

options = build_options_from_state()
optimize_level = st.session_state.get("optimize_level", "basic")

# File upload
uploaded_files = st.file_uploader(
    "选择多个图片文件",
    type=["png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.markdown(f"**已选择 {len(uploaded_files)} 个文件**")

    if st.button("▶ 开始批量转换", type="primary", use_container_width=True):
        progress_bar = st.progress(0, text="准备转换…")
        results: list[dict] = []
        total = len(uploaded_files)

        for i, uploaded in enumerate(uploaded_files):
            progress_bar.progress(i / total, text=f"正在转换 {uploaded.name}…")
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    tmp_dir = Path(tmp)
                    input_path = tmp_dir / uploaded.name
                    input_path.write_bytes(uploaded.getvalue())
                    svg_path = tmp_dir / f"{Path(uploaded.name).stem}.svg"

                    result = trace_image(
                        input_path,
                        svg_path,
                        options,
                        optimize=True,
                        optimize_level=optimize_level,
                    )
                    results.append(
                        {
                            "name": uploaded.name,
                            "svg_bytes": result.svg_path.read_bytes(),
                            "stats": result.stats,
                            "elapsed": result.elapsed_seconds,
                            "engine": result.engine,
                        }
                    )
                    try:
                        record_task(result, current_preset, options)
                    except Exception:
                        pass
            except Exception as e:
                results.append({"name": uploaded.name, "error": str(e)})

        progress_bar.progress(1.0, text="批量转换完成")
        st.session_state.batch_results = results
        success_count = len([r for r in results if "error" not in r])
        st.session_state["ui_message"] = (
            "success",
            f"批量转换完成: {success_count}/{total} 成功",
        )
        st.rerun()

    # Results list
    if st.session_state.get("batch_results"):
        st.divider()
        st.markdown("### 结果列表")
        for r in st.session_state.batch_results:
            cols = st.columns([3, 1, 1])
            with cols[0]:
                if "error" in r:
                    st.error(f"❌ {r['name']}: {r['error']}")
                else:
                    st.success(
                        f"✅ {r['name']} — {r['stats'].get('paths', 0)} 路径 | {r['elapsed']:.2f}s"
                    )
            with cols[1]:
                if "error" not in r:
                    st.download_button(
                        "下载",
                        data=r["svg_bytes"],
                        file_name=f"{Path(r['name']).stem}.svg",
                        mime="image/svg+xml",
                        key=f"dl_batch_{r['name']}",
                    )
            with cols[2]:
                if "error" not in r:
                    if st.button("复用参数", key=f"reuse_batch_{r['name']}"):
                        st.session_state.preset_selector = st.session_state.get(
                            "batch_preset", "poster"
                        )
                        st.session_state["ui_message"] = (
                            "success",
                            f"已加载 {r['name']} 的参数",
                        )
                        st.switch_page("app_pages/01_Convert.py")

        if st.button("🗑 清空批量结果"):
            st.session_state.batch_results = []
            st.rerun()
