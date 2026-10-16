import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("👥 Admin端 · 客流场景设置")
st.caption("所有客流数据均为仿真设定（D类），不代表景区实测值")

# 初始化状态
if "scenario" not in st.session_state:
    st.session_state.scenario = {
        "type": "平峰",
        "arrival_rate": 120,
        "duration_min": 600,
        "seed": 42,
    }
sc = st.session_state.scenario

with st.container(border=True):
    st.subheader("场景类型")
    sc["type"] = st.radio(
        "选择客流模式",
        ["平峰", "上午高峰", "下午高峰"],
        horizontal=True,
        index=["平峰", "上午高峰", "下午高峰"].index(sc["type"]),
    )

with st.container(border=True):
    st.subheader("客流参数")
    sc["arrival_rate"] = st.slider("基准到达率（人/小时）", 30, 600, sc["arrival_rate"], 10)
    sc["duration_min"] = st.number_input("仿真时长（分钟）", 60, 720, sc["duration_min"], 30)
    sc["seed"] = st.number_input("随机种子", 0, 9999, sc["seed"])


# ========= 核心：按场景生成不同形状的曲线 =========
def generate_demand_curve(sc):
    """
    生成分时段到达曲线
    返回：(时间段列表, 各段到达人数)
    """
    # 每15分钟一个点
    t = np.arange(0, sc["duration_min"], 15)
    # 每15分钟的基础到达人数 = 每小时人数 / 4
    base = sc["arrival_rate"] / 4

    if sc["type"] == "平峰":
        # 平峰：全天基本稳定，有微弱波动
        y = base * (1 + 0.1 * np.sin(t / 60 * np.pi))

    elif sc["type"] == "上午高峰":
        # 上午高峰：假设仿真从 8:00 开始，高峰在 10:00 左右（即第 120 分钟）
        center = 120
        sigma = 60  # 高峰持续时间参数
        peak = np.exp(-((t - center) ** 2) / (2 * sigma ** 2))
        # 峰值高度为基准的 3 倍
        y = base * (1 + 2.0 * peak)

    elif sc["type"] == "下午高峰":
        # 下午高峰：假设高峰在 16:00 左右（即第 480 分钟）
        center = 480
        sigma = 60
        peak = np.exp(-((t - center) ** 2) / (2 * sigma ** 2))
        y = base * (1 + 2.0 * peak)

    else:
        y = base * np.ones_like(t, dtype=float)

    return t, y


# 生成曲线
t, y = generate_demand_curve(sc)

with st.container(border=True):
    st.subheader("📈 到达曲线预览")
    st.caption("按 15 分钟粒度统计的到达人数（仿真设定，非实测）")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t,
        y=y,
        mode="lines+markers",
        line=dict(color="#1E6F5C", width=3),
        marker=dict(size=6),
        name="到达人数",
        fill="tozeroy",
        fillcolor="rgba(30, 111, 92, 0.15)",
    ))

    fig.update_layout(
        height=350,
        xaxis_title="时间（分钟）",
        yaxis_title="到达人数 / 15min",
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)

    # 显示峰值信息
    peak_idx = int(np.argmax(y))
    peak_time = t[peak_idx]
    peak_value = y[peak_idx]
    c1, c2, c3 = st.columns(3)
    c1.metric("基准到达率", f"{sc['arrival_rate']} 人/h")
    c2.metric("峰值到达率", f"{peak_value*4:.0f} 人/h")
    c3.metric("高峰时刻", f"第 {peak_time:.0f} 分钟")

st.success("✅ 场景已保存")