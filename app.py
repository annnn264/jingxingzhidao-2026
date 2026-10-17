"""景行智调 · 单网站双入口（Admin / User）统一启动文件。"""
import streamlit as st
from utils.style import load_css

st.set_page_config(
    page_title="景行智调 · 景区接驳车仿真",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_css()

pages = {
    "Admin 管理端": [
        st.Page("pages/0_Admin_Home.py", title="入口说明", icon="🏠", default=True),
        st.Page("pages/1_Admin_Dashboard.py", title="调度控制台", icon="🎛️"),
        st.Page("pages/2_Admin_Vehicle_Route.py", title="车辆与线路", icon="🚌"),
        st.Page("pages/3_Admin_Demand_Scenario.py", title="客流场景", icon="👥"),
        st.Page("pages/4_Admin_Smart_Dispatch.py", title="智能调度", icon="🧠"),
        st.Page("pages/5_Admin_Simulation_Monitor.py", title="仿真监测", icon="📡"),
        st.Page("pages/6_Admin_Experiment_Analysis.py", title="实验分析", icon="📊"),
    ],
    "User 游客端": [
        st.Page("pages/User_Placeholder.py", title="游客交互（待接入）", icon="📍"),
    ],
}

# 目前两个菜单处于同一网站、同一浏览器会话。跨浏览器共享结果需数据库/API，
# 不能依赖 Streamlit session_state。User队友的正式页面交付后替换占位页。
current_page = st.navigation(pages, position="top")
current_page.run()
