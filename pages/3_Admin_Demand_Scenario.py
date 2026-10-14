import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("👥 Admin端 · 客流场景设置")
st.caption("所有客流数据均为仿真设定（D类）")

if "scenario" not in st.session_state:
    st.session_state.scenario = {
        "type": "平峰",
        "arrival_rate": 120,
        "duration_min": 600,
        "seed": 42,
    }
sc = st.session_state.scenario

with st.container(border=True):
    sc["type"] = st.radio("场景类型", ["平峰", "上午高峰", "下午高峰"], horizontal=True,
                          index=["平峰", "上午高峰", "下午高峰"].index(sc["type"]))
    sc["arrival_rate"] = st.slider("到达率（人/小时）", 30, 600, sc["arrival_rate"], 10)
    sc["duration_min"] = st.number_input("仿真时长（分钟）", 60, 720, sc["duration_min"], 30)
    sc["seed"] = st.number_input("随机种子", 0, 9999, sc["seed"])

with st.container(border=True):
    st.subheader("📈 到达曲线预览")
    t = np.arange(0, sc["duration_min"], 15)
    fig = go.Figure(go.Scatter(x=t, y=[sc["arrival_rate"]/4]*len(t),
                                mode="lines+markers", line=dict(color="#1E6F5C", width=3)))
    fig.update_layout(height=280, xaxis_title="时间（分钟）", yaxis_title="到达人数/15min")
    st.plotly_chart(fig, use_container_width=True)

st.success("✅ 场景已保存")