import streamlit as st
import plotly.graph_objects as go

st.title("📡 Admin端 · 仿真监测")

if "result" not in st.session_state:
    st.info("👉 请先在「智能调度控制」运行一次仿真")
    st.stop()

r = st.session_state["result"]

with st.container(border=True):
    st.subheader("各站点剩余排队")
    fig = go.Figure(go.Bar(
        x=list(r["stations"].keys()),
        y=list(r["stations"].values()),
        marker_color="#1E6F5C",
        text=list(r["stations"].values()),
        textposition="outside",
    ))
    fig.update_layout(height=350, yaxis_title="排队（人）")
    st.plotly_chart(fig, use_container_width=True)

with st.container(border=True):
    st.subheader("等待时间分布")
    fig2 = go.Figure(go.Histogram(x=r["waits"], nbinsx=30, marker_color="#F6BD16"))
    fig2.update_layout(height=350, xaxis_title="等待（min）")
    st.plotly_chart(fig2, use_container_width=True)

st.markdown('<div class="footer-text">⚠️ 所有结果由程序生成，不代表景区实测。</div>', unsafe_allow_html=True)