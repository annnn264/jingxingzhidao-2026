import streamlit as st
from core.simulation import run_simulation
from utils.data_check import check_p0

st.title("🧠 Admin端 · 智能调度控制")

if "scenario" not in st.session_state:
    st.warning("⚠️ 请先到「客流场景设置」配置参数")
    st.stop()

mode = st.radio("运行模式", ["仿真模式", "真实模式"], horizontal=True)
check_p0(mode="real" if mode == "真实模式" else "sim")

strategy = st.radio("调度策略", ["固定调度", "动态调度"], horizontal=True)

with st.container(border=True):
    if strategy == "固定调度":
        fixed_interval = st.slider("发车间隔（分钟）", 15, 20, 17)
        st.caption("官方回复：常规发车间隔 15–20 分钟")
        queue_threshold = None
    else:
        fixed_interval = 17
        queue_threshold = st.slider("排队触发阈值（人）", 5, 100, 20)

    speed_kmh = st.slider("行驶速度（km/h）", 5, 20, 15)
    st.caption("速度范围 5–20 km/h（仿真可调）")

if st.button("🚀 开始仿真", type="primary", use_container_width=True):
    params = {
        "duration_min": st.session_state.scenario["duration_min"],
        "arrival_rate": st.session_state.scenario["arrival_rate"],
        "fleet": {"A": 5, "B": 3},
        "fixed_interval": fixed_interval,
        "speed_kmh": speed_kmh,
        "queue_threshold": queue_threshold or 20,
    }
    with st.spinner("仿真运行中..."):
        res = run_simulation(
            params,
            strategy="fixed" if strategy == "固定调度" else "dynamic"
        )
    st.session_state["result"] = res
    st.success("✅ 仿真完成")

if "result" in st.session_state:
    r = st.session_state["result"]
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("平均等待", f"{r['avg_wait']:.1f} min")
    c2.metric("最大等待", f"{r['max_wait']:.1f} min")
    c3.metric("超阈值比例", f"{r['over_ratio']*100:.1f}%")
    c4.metric("完成运输", r["served"])

st.markdown('<div class="footer-text">⚠️ 所有结果由程序生成，不代表景区实测。</div>', unsafe_allow_html=True)