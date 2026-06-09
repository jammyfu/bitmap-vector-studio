"""历史记录页面 — 最近任务列表与参数复用、报告导出与统计仪表盘."""

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
from vector_studio.report_generator import BatchReport, ConversionReport, ReportGenerator
from vector_studio.stats_dashboard import StatsDashboard

st.title("🕐 历史记录")
st.caption("最近转换任务")

show_ui_message()

# ---------------------------------------------------------------------------
# 统计仪表盘
# ---------------------------------------------------------------------------
with st.expander("📊 统计仪表盘", expanded=False):
    days = st.slider("统计天数", min_value=7, max_value=90, value=30, key="stats_days")
    dashboard = StatsDashboard()
    summary = dashboard.get_summary(days=days)
    trend = dashboard.get_daily_trend(days=min(days, 14))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("总转换数", summary["total_conversions"])
    c2.metric("成功", summary["successful"])
    c3.metric("成功率", f"{summary['success_rate']:.1f}%")
    c4.metric("平均耗时", f"{summary['average_duration']:.2f}s")

    if trend:
        st.bar_chart(
            {day["date"]: day["count"] for day in trend},
            use_container_width=True,
        )

    if summary["top_presets"]:
        st.markdown("**常用预设**")
        for preset_name, count in summary["top_presets"]:
            st.markdown(f"- `{preset_name}`: {count} 次")

# ---------------------------------------------------------------------------
# 历史任务列表
# ---------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------
    # 报告导出
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown("**📄 报告导出**")
    export_cols = st.columns(3)
    with export_cols[0]:
        if st.button("导出 JSON", key="export_json"):
            _export_history_report(tasks, "json")
    with export_cols[1]:
        if st.button("导出 Markdown", key="export_md"):
            _export_history_report(tasks, "md")
    with export_cols[2]:
        if st.button("导出 CSV", key="export_csv"):
            _export_history_report(tasks, "csv")

    if st.button("🗑 清空历史记录", type="secondary"):
        try:
            clear_history()
            st.session_state["ui_message"] = ("success", "历史记录已清空")
            st.rerun()
        except Exception as e:
            st.session_state["ui_message"] = ("error", f"清空失败: {e}")
            st.rerun()


def _export_history_report(tasks: list[dict], fmt: str) -> None:
    """将历史任务列表导出为指定格式的报告."""
    items: list[ConversionReport] = []
    total_input = 0
    total_output = 0
    total_duration = 0.0

    for task in tasks:
        input_path = task.get("input_path", "")
        output_path = task.get("output_path", "")
        input_size = 0
        try:
            input_size = Path(input_path).stat().st_size if input_path else 0
        except Exception:
            pass
        output_size = 0
        try:
            output_size = Path(output_path).stat().st_size if output_path else 0
        except Exception:
            pass

        total_input += input_size
        total_output += output_size
        elapsed = task.get("elapsed_seconds", 0.0)
        total_duration += elapsed

        items.append(
            ConversionReport(
                input_file=input_path,
                output_file=output_path,
                input_size_bytes=input_size,
                output_size_bytes=output_size,
                compression_ratio=input_size / output_size if output_size > 0 else 0.0,
                preset_used=task.get("preset_name", "unknown"),
                parameters=task.get("options", {}),
                quality_score=None,
                path_count=task.get("stats", {}).get("paths"),
                color_count=task.get("stats", {}).get("colors"),
                duration_seconds=elapsed,
                timestamp=task.get("timestamp", ""),
            )
        )

    report = BatchReport(
        total_files=len(tasks),
        successful=len(tasks),
        failed=0,
        total_input_size=total_input,
        total_output_size=total_output,
        average_duration=total_duration / len(tasks) if tasks else 0.0,
        preset_used=tasks[0].get("preset_name", "mixed") if tasks else "unknown",
        items=items,
        timestamp=__import__("datetime").datetime.now().isoformat(),
    )

    gen = ReportGenerator()
    try:
        path = gen.save_report(report, format=fmt)
        st.session_state["ui_message"] = ("success", f"报告已保存: {path.name}")
    except Exception as e:
        st.session_state["ui_message"] = ("error", f"导出失败: {e}")
    st.rerun()
