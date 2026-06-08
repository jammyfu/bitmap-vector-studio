"""设置页面 — 主题、默认参数与外部编辑器."""

from __future__ import annotations

import streamlit as st

from app_pages._shared import (
    get_config,
    save_config,
    show_ui_message,
    _HAS_CONFIG,
    _HAS_EDITORS,
)

st.title("⚙️ 设置")
st.caption("偏好配置")

show_ui_message()

# ---------------------------------------------------------------------------
# 外观
# ---------------------------------------------------------------------------
st.markdown("### 外观")
theme = st.radio(
    "主题",
    ["light", "dark"],
    index=0 if st.session_state.get("theme", "light") == "light" else 1,
    horizontal=True,
)
st.session_state.theme = theme

# ---------------------------------------------------------------------------
# 默认参数
# ---------------------------------------------------------------------------
st.markdown("### 默认参数")
default_preset = st.selectbox(
    "默认预设",
    ["poster", "logo", "photo", "bw", "scan", "pixel_art"],
    index=0,
)
default_optimize = st.selectbox(
    "默认优化级别",
    ["basic", "comprehensive", "aggressive"],
    index=0,
)
default_format = st.selectbox(
    "默认输出格式",
    ["SVG", "SVG + PDF", "SVG + PNG"],
    index=0,
)

# ---------------------------------------------------------------------------
# 外部编辑器
# ---------------------------------------------------------------------------
st.markdown("### 外部编辑器")
if _HAS_EDITORS:
    try:
        from vector_studio.external_editors import detect_editors

        editors = detect_editors()
        available = [e.display_name for e in editors if e.is_available]
    except Exception:
        available = []
    editor_options = ["系统默认"] + available
    selected_editor = st.selectbox("首选编辑器", editor_options, index=0)
else:
    st.caption("外部编辑器检测不可用")
    selected_editor = "系统默认"

# ---------------------------------------------------------------------------
# 语言
# ---------------------------------------------------------------------------
st.markdown("### 语言")
lang = st.selectbox("界面语言", ["简体中文", "English"], index=0)
st.caption("（语言切换将在重启后生效）")

# ---------------------------------------------------------------------------
# 保存 / 重置
# ---------------------------------------------------------------------------
if st.button("💾 保存设置", type="primary", use_container_width=True):
    if _HAS_CONFIG:
        try:
            from vector_studio.config import Config

            cfg = get_config() or Config()
            cfg.default_preset = default_preset
            cfg.default_optimize_level = default_optimize
            if selected_editor != "系统默认":
                cfg.editor_preference = selected_editor
            save_config(cfg)
            st.session_state["ui_message"] = ("success", "设置已保存")
            st.rerun()
        except Exception as e:
            st.session_state["ui_message"] = ("error", f"保存失败: {e}")
            st.rerun()
    else:
        st.session_state["ui_message"] = ("warning", "配置模块不可用，设置仅当前会话有效")
        st.rerun()

if st.button("🔄 恢复默认设置", type="secondary"):
    if _HAS_CONFIG:
        try:
            from vector_studio.config import Config

            save_config(Config())
            st.session_state["ui_message"] = ("success", "已恢复默认设置")
            st.rerun()
        except Exception as e:
            st.session_state["ui_message"] = ("error", f"恢复失败: {e}")
            st.rerun()
    else:
        st.session_state["ui_message"] = ("warning", "配置模块不可用")
        st.rerun()
