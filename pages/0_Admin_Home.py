"""Admin 菜单首页；原 app.py 的入口内容移入这里。"""
import streamlit as st

st.title("🚌 景行智调 · 调度控制台")
st.caption("景区接驳车智能调度与可视化决策系统 · 研究型仿真原型")
st.info("请从网站顶部的「Admin 管理端」进入客流设置、智能调度、仿真监测等模块。"
        "「User 游客端」目前是联调占位页，后续替换为队友提供的正式游客界面。")

c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.subheader("🚌 车辆与线路")
        st.write("站点、线路及估算路段距离；车辆数可在调度页调整。")
with c2:
    with st.container(border=True):
        st.subheader("🧠 智能调度")
        st.write("固定间隔、动态阈值和滚动预测三种策略。")
with c3:
    with st.container(border=True):
        st.subheader("📊 仿真监测")
        st.write("真实读取本轮仿真记录，支持导出四份CSV。")

st.caption("⚠️ 车队规模、客流、双向折返等属于模型假设；结果不是钟山风景区实测数据。")
