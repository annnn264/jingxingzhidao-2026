import streamlit as st
import plotly.graph_objects as go

st.title("🎛️ Admin端 · 调度控制台")
st.caption("面向景区运营调度员")

c1, c2, c3, c4 = st.columns(4)
c1.metric("A线车辆", "5 辆")
c2.metric("B线车辆", "3 辆")
c3.metric("车型容量", "22/36/40 座")
c4.metric("发车间隔", "15–20 min")

st.markdown("---")

col_left, col_right = st.columns([2, 1])

with col_left:
    with st.container(border=True):
        st.subheader("📈 线路长度对比")
        fig = go.Figure(go.Bar(
            x=["A线 钟灵街游览线", "B线 紫金·钟爱里线"],
            y=[3.1, 6.5],
            marker_color=["#1E6F5C", "#F6BD16"],
            text=[3.1, 6.5],
            textposition="outside",
        ))
        fig.update_layout(height=300, yaxis_title="总长度（km）")
        st.plotly_chart(fig, use_container_width=True)

with col_right:
    with st.container(border=True):
        st.subheader("📢 数据状态")
        st.success("A/B线站序、总长、分段距离已录入")
        st.warning("逐站客流、折返时间为仿真设定")
        st.info("数据来源：V2 参数表 + 景区访谈")

st.markdown("---")
st.subheader("🧭 快捷入口")
q1, q2, q3 = st.columns(3)
with q1:
    if st.button("🚌 车辆与线路", use_container_width=True):
        st.switch_page("pages/2_Admin_Vehicle_Route.py")
with q2:
    if st.button("🧠 智能调度", use_container_width=True):
        st.switch_page("pages/4_Admin_Smart_Dispatch.py")
with q3:
    if st.button("📊 实验分析", use_container_width=True):
        st.switch_page("pages/6_Admin_Experiment_Analysis.py")

st.markdown('<div class="footer-text">⚠️ 本系统为仿真原型，结果由程序生成，不代表景区实测结果。</div>', unsafe_allow_html=True)