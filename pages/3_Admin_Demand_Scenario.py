import streamlit as st
import numpy as np
import plotly.graph_objects as go

st.title("👥 Admin端 · 客流场景设置")
st.caption("所有客流数据均为仿真设定（D类），不代表景区实测值")

# ============ 初始化状态 ============
if "scenario" not in st.session_state:
    st.session_state.scenario = {
        "type": "平峰",
        "arrival_rate": 120,
        "duration_min": 600,
        "seed": 42,
        "tidal": False,          # 是否启用潮汐
        "disruption": False,     # 是否启用突发
        "disruption_type": "客流突增",
        "disruption_center": 300,# 突发中心时刻（分钟）
        "disruption_sigma": 30,  # 突发持续宽度（分钟）
        "disruption_intensity": 2.0,  # 突发强度倍数
    }
sc = st.session_state.scenario

# ============ 场景基础参数 ============
with st.container(border=True):
    st.subheader("① 基础场景")
    sc["type"] = st.radio(
        "客流模式",
        ["平峰", "上午高峰", "下午高峰"],
        horizontal=True,
        index=["平峰", "上午高峰", "下午高峰"].index(sc["type"]),
    )

    col1, col2 = st.columns(2)
    with col1:
        sc["arrival_rate"] = st.slider("基准到达率（人/小时）", 30, 600, sc["arrival_rate"], 10)
    with col2:
        sc["duration_min"] = st.number_input("仿真时长（分钟）", 60, 720, sc["duration_min"], 30)

# ============ 潮汐客流开关 ============
with st.container(border=True):
    st.subheader("② 节假日潮汐客流")
    st.caption("开启后，客流呈现明显的方向切换：上午上山为主，下午下山为主")
    sc["tidal"] = st.checkbox("启用潮汐客流（节假日典型模式）", value=sc["tidal"])

# ============ 突发情况 ============
with st.container(border=True):
    st.subheader("③ 突发情况模拟")
    st.caption("模拟客流突增、骤降等异常事件")
    sc["disruption"] = st.checkbox("启用突发情况", value=sc["disruption"])

    if sc["disruption"]:
        sc["disruption_type"] = st.selectbox(
            "突发类型",
            ["客流突增", "客流骤降", "双向高峰"],
            index=["客流突增", "客流骤降", "双向高峰"].index(sc["disruption_type"]),
        )
        col1, col2, col3 = st.columns(3)
        with col1:
            sc["disruption_center"] = st.number_input(
                "触发时刻（分钟）", 0, sc["duration_min"], sc["disruption_center"], 15)
        with col2:
            sc["disruption_sigma"] = st.number_input(
                "持续宽度（分钟）", 5, 180, sc["disruption_sigma"], 5)
        with col3:
            sc["disruption_intensity"] = st.slider(
                "影响强度（倍）", 0.2, 5.0, sc["disruption_intensity"], 0.1)

sc["seed"] = st.number_input("随机种子", 0, 9999, sc["seed"])


# ================================================================
# 核心：生成客流曲线（基础 + 潮汐 + 突发）
# ================================================================
def generate_curve(sc):
    """
    返回：
        t                 : 时间点列表
        y_up              : 上行（上山/进景区）到达人数
        y_down            : 下行（下山/出景区）到达人数
    """
    t = np.arange(0, sc["duration_min"], 15)
    base = sc["arrival_rate"] / 4  # 每15分钟基础人数

    # -------- 1. 基础曲线 --------
    if sc["type"] == "平峰":
        y_up = base * (1 + 0.1 * np.sin(t / 60 * np.pi)) * 0.6
        y_down = base * (1 + 0.1 * np.cos(t / 60 * np.pi)) * 0.4

    elif sc["type"] == "上午高峰":
        center = sc["duration_min"] * 0.25
        sigma = sc["duration_min"] * 0.15
        peak = np.exp(-((t - center) ** 2) / (2 * sigma ** 2))
        y_up = base * (1 + 2.0 * peak) * 0.8
        y_down = base * (1 + 0.3 * peak) * 0.2

    elif sc["type"] == "下午高峰":
        center = sc["duration_min"] * 0.75
        sigma = sc["duration_min"] * 0.15
        peak = np.exp(-((t - center) ** 2) / (2 * sigma ** 2))
        y_up = base * (1 + 0.3 * peak) * 0.2
        y_down = base * (1 + 2.0 * peak) * 0.8

    else:
        y_up = base * 0.5 * np.ones_like(t, dtype=float)
        y_down = base * 0.5 * np.ones_like(t, dtype=float)

    # -------- 2. 潮汐客流 --------
    if sc["tidal"]:
        # 上午（前 1/3）：上行增强
        # 下午（后 1/3）：下行增强
        morning_boost = np.exp(-((t - sc["duration_min"] * 0.25) ** 2) /
                                (2 * (sc["duration_min"] * 0.18) ** 2))
        afternoon_boost = np.exp(-((t - sc["duration_min"] * 0.75) ** 2) /
                                  (2 * (sc["duration_min"] * 0.18) ** 2))
        y_up = y_up * (1 + 1.2 * morning_boost)
        y_down = y_down * (1 + 1.2 * afternoon_boost)

    # -------- 3. 突发情况 --------
    if sc["disruption"]:
        center = sc["disruption_center"]
        sigma = sc["disruption_sigma"]
        intensity = sc["disruption_intensity"]
        burst = np.exp(-((t - center) ** 2) / (2 * sigma ** 2))

        if sc["disruption_type"] == "客流突增":
            y_up = y_up * (1 + (intensity - 1) * burst)
            y_down = y_down * (1 + (intensity - 1) * burst * 0.5)

        elif sc["disruption_type"] == "客流骤降":
            y_up = y_up * (1 - (1 - intensity) * burst)
            y_down = y_down * (1 - (1 - intensity) * burst)

        elif sc["disruption_type"] == "双向高峰":
            y_up = y_up * (1 + (intensity - 1) * burst)
            y_down = y_down * (1 + (intensity - 1) * burst)

    return t, y_up, y_down


# ================================================================
# 绘图
# ================================================================
t, y_up, y_down = generate_curve(sc)

with st.container(border=True):
    st.subheader("📈 客流曲线预览")
    st.caption("按 15 分钟粒度统计的到达人数（仿真设定，非实测）")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t, y=y_up, mode="lines+markers",
        name="上行（上山 / 进景区）",
        line=dict(color="#1E6F5C", width=3),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=t, y=y_down, mode="lines+markers",
        name="下行（下山 / 出景区）",
        line=dict(color="#F6BD16", width=3),
        marker=dict(size=5),
    ))

    fig.update_layout(
        height=400,
        xaxis_title="时间（分钟）",
        yaxis_title="到达人数 / 15min",
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig, use_container_width=True)

    # 峰值信息
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("基准到达率", f"{sc['arrival_rate']} 人/h")
    c2.metric("上行峰值", f"{y_up.max()*4:.0f} 人/h")
    c3.metric("下行峰值", f"{y_down.max()*4:.0f} 人/h")
    c4.metric("总到达量", f"{(y_up.sum() + y_down.sum()):.0f} 人")

st.success("✅ 场景已保存，可进入「智能调度控制」页运行仿真")