import streamlit as st
from utils.style import load_css

st.set_page_config(
    page_title="景行智调 · 调度控制台",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()

st.markdown('<div class="main-title">🚌 景行智调 · 调度控制台</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">景区接驳车智能调度与可视化决策系统 · Admin 端</div>', unsafe_allow_html=True)

st.info("👈 请从左侧导航进入各功能页面：控制台 → 车辆线路 → 客流场景 → 智能调度 → 仿真监测 → 实验分析")

st.markdown("---")

col1, col2, col3 = st.columns(3)
with col1:
    with st.container(border=True):
        st.markdown("#### 🚌 车辆与线路管理")
        st.write("站点、线路、分段距离、车辆参数。")
with col2:
    with st.container(border=True):
        st.markdown("#### 🧠 智能调度控制")
        st.write("固定/动态调度策略，一键运行仿真。")
with col3:
    with st.container(border=True):
        st.markdown("#### 📊 仿真监测与分析")
        st.write("实时状态、等待分布、实验对比。")

st.markdown("---")
st.caption("⚠️ 本系统为仿真原型，结果由程序生成，不代表景区实测结果。")