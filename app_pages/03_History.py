"""历史记录页面 — 最近任务列表与参数复用."""

from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

from app_pages._shared import (
    apply_preset_values,
    clear_history,
    get_recent_tasks,
    get_task_options,
    show_ui_message,
)

st.title("🕐 历史记录")
st.caption("最近转换任务")

show_ui_message()

tasks = get_recent_tasks(20)

if not tasks:
    st.info("暂无历史记录")
else:
    st.markdown(f"**最近 {len(tasks)} 条记录**")
    for task in tasks:
        task_id = task.get("task_id", "")
        input_name = Path(task.get("input_path", "unknown")).name
        preset = task.get("preset_name", "-")
        elapsed = task.get("elapsed_seconds", 0)
        paths = task.get("stats", {}).get("paths", 0)
        timestamp = task.get("timestamp", "-")

        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            with c1:
                st.markdown(
                    f"**{html.escape(input_name)}**  \n"
                    f"<small>预设: `{preset}` | 耗时: {elapsed:.2f}s | "
                    f"路径: {paths} | {timestamp[:19]}</small>",
                    unsafe_allow_html=True,
                )
            with c2:
                if st.button("复用参数", key=f"reuse_{task_id}"):
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
                        if recorded_preset:
                            st.session_state.preset_selector = recorded_preset
                        st.session_state["ui_message"] = ("success", "已加载历史任务参数")
                        st.switch_page("app_pages/01_Convert.py")
                    except Exception as e:
                        st.session_state["ui_message"] = ("error", f"加载失败: {e}")
                        st.rerun()

    if st.button("🗑 清空历史记录", type="secondary"):
        try:
            clear_history()
            st.session_state["ui_message"] = ("success", "历史记录已清空")
            st.rerun()
        except Exception as e:
            st.session_state["ui_message"] = ("error", f"清空失败: {e}")
            st.rerun()
