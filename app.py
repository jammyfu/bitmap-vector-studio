import streamlit as st

st.set_page_config(
    page_title="Bitmap Vector Studio",
    page_icon="🎨",
    layout="centered",
    initial_sidebar_state="collapsed",
)

from app_pages._shared import init_session_state

init_session_state()

pg = st.navigation([
    st.Page("app_pages/01_Convert.py", title="转换", icon="🎨"),
    st.Page("app_pages/02_Batch.py", title="批量", icon="📁"),
    st.Page("app_pages/03_History.py", title="历史", icon="🕐"),
    st.Page("app_pages/04_Settings.py", title="设置", icon="⚙️"),
])
pg.run()
