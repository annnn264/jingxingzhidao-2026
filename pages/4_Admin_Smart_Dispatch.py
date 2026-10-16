"""可调整车队 + 三策略同场景对比。所有规模均为模拟参数。"""
import streamlit as st
import pandas as pd
from core.simulation import run_simulation
from data.vehicles import DEFAULT_FLEET
from utils.data_check import check_p0

st.title("🧠 Admin端 · 智能调度控制")
if "scenario" not in st.session_state:
    st.warning("⚠️ 请先到「客流场景设置」配置参数")
    st.stop()

mode = st.radio("运行模式", ["仿真模式", "真实模式（尚未接入）"], horizontal=True)
check_p0(mode="real" if mode != "仿真模式" else "sim")

st.subheader("🚌 车队规模（模型输入，不代表景区实际数量）")
if "fleet" not in st.session_state:
    st.session_state.fleet = dict(DEFAULT_FLEET)
col_a, col_b, col_c = st.columns(3)
with col_a:
    n_a = st.number_input("A线可用车辆（辆）", min_value=0, max_value=150,
                          value=int(st.session_state.fleet.get("A", 5)), step=1)
with col_b:
    n_b = st.number_input("B线可用车辆（辆）", min_value=0, max_value=150,
                          value=int(st.session_state.fleet.get("B", 3)), step=1)
with col_c:
    capacity = st.selectbox("单车容量（座，模型假设）", [22, 36, 40], index=1)
# 不依赖A/B固定数；只有在当前页面提交本次配置时才使实验记录包含此值。
st.session_state.fleet = {"A": int(n_a), "B": int(n_b)}
st.info(f"当前模拟车队：A线 {n_a} 辆、B线 {n_b} 辆，合计 {n_a+n_b} 辆；"
        "常规不跨线调配。40座仅为‘40余座’车型的简化实验档位。")

strategy_labels = {
    "固定间隔调度": "fixed", "排队阈值响应": "dynamic", "滚动预测优化（MPC+束搜索）": "optimized"
}
strategy_label = st.radio("调度策略", list(strategy_labels), horizontal=False)

with st.container(border=True):
    c1, c2, c3 = st.columns(3)
    with c1:
        fixed_interval = st.slider("固定调度间隔（分钟）", 5, 40, 17)
    with c2:
        queue_threshold = st.slider("阈值调度触发排队（人）", 5, 150, 20)
    with c3:
        speed_kmh = st.slider("假设平均速度（km/h）", 5, 20, 15)
    st.caption("20km/h是情景速度上限，不代表景区已核实限速。双向沿相同道路折返属于仿真假设。")

with st.expander("⚙️ 优化算法参数（默认可用，必要时调整）"):
    c1, c2, c3 = st.columns(3)
    with c1:
        decision_interval_min = st.selectbox("滚动决策间隔（分钟）", [2, 5, 10], index=1)
        dispatch_penalty = st.number_input("每次发车惩罚（等效人·分钟）", 0.0, 200.0, 15.0, 5.0)
    with c2:
        prediction_horizon_min = st.selectbox("预测范围（分钟）", [20, 30, 45, 60], index=2)
        terminal_backlog_weight = st.number_input("期末积压权重", 0.0, 10.0, 1.0, 0.25)
    with c3:
        beam_width = st.slider("束搜索宽度", 2, 12, 5)
        fairness_weight = st.number_input("长等待额外惩罚权重", 0.0, 4.0, 0.35, 0.05)
    st.caption("算法按当前可观测队列和短时需求预测评估方案，不读取仿真未来真实到达事件。"
               " 预测模型为近似模型，实际效果以离散事件仿真验证为准。")

sc = st.session_state.scenario
params = {
    "duration_min": int(sc["duration_min"]),
    "arrival_rate": float(sc["arrival_rate"]),
    "scenario_type": sc["type"],
    "peak_multiplier": float(sc.get("peak_multiplier", 2.0)),
    "fleet": dict(st.session_state.fleet),
    "vehicle_capacities": {rid: [int(capacity)] * cnt for rid, cnt in st.session_state.fleet.items()},
    "fixed_interval": float(fixed_interval),
    "speed_kmh": float(speed_kmh),
    "queue_threshold": int(queue_threshold),
    "decision_interval_min": float(decision_interval_min),
    "prediction_horizon_min": float(prediction_horizon_min),
    "beam_width": int(beam_width),
    "dispatch_penalty": float(dispatch_penalty),
    "terminal_backlog_weight": float(terminal_backlog_weight),
    "fairness_weight": float(fairness_weight),
}
seed = int(sc["seed"])

def run_group(strategies):
    with st.spinner("正在计算仿真与优化结果..."):
        return [run_simulation(params, strategy=s, seed=seed) for s in strategies]

if st.button("🚀 运行所选策略", type="primary", use_container_width=True):
    result = run_group([strategy_labels[strategy_label]])[0]
    st.session_state["result"] = result
    st.session_state.pop("comparison", None)
    st.success("仿真已完成")

if st.button("📊 同场景对比三种策略", use_container_width=True):
    cmp = run_group(["fixed", "dynamic", "optimized"])
    if len({r["demand_signature"] for r in cmp}) != 1:
        st.error("三种策略的需求不一致，禁止对比")
    else:
        st.session_state["comparison"] = cmp
        st.session_state["result"] = cmp[-1]
        st.success("对比完成；监测页面展示优化策略结果")

if "result" in st.session_state:
    r = st.session_state["result"]
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全体到达者的已观察候车均值", f"{r['avg_observed_wait_all']:.1f} min")
    c2.metric("已上车游客P95候车", f"{r['p95_wait']:.1f} min" if r['served'] else "—")
    c3.metric("未上车人数", r["unserved"])
    c4.metric("上车服务率", f"{r['service_rate']*100:.1f}%")
    st.caption("‘已观察候车均值’对未上车游客统计到仿真截止时为止的等待，属于删失下界；"
               "不是所有游客最终完整候车时长。")
    st.caption(f"A线 {r['params']['fleet'].get('A', 0)}辆，B线 {r['params']['fleet'].get('B', 0)}辆；"
               f"到达 {r['total_arrivals']}人，上车 {r['served']}人，期末仍在排队 {r['unserved']}人；"
               f"共发车 {r['total_departures']}趟。")

if "comparison" in st.session_state:
    cmp = st.session_state["comparison"]
    st.subheader("📈 相同客流、车队及速度的三策略对比")
    st.dataframe(pd.DataFrame([{
        "策略": {"fixed": "固定间隔", "dynamic": "队列阈值", "optimized": "滚动优化"}[x["strategy"]],
        "已观察候车总量（人·分钟）": round(x["total_wait_person_min"], 1),
        "已观察候车均值（分钟/人）": round(x["avg_observed_wait_all"], 2),
        "已上车者P95（分钟）": round(x["p95_wait"], 2),
        "未上车人数": x["unserved"],
        "上车服务率(%)": round(100*x["service_rate"], 2),
        "发车趟数": x["total_departures"],
    } for x in cmp]), hide_index=True, use_container_width=True)
    st.caption("注意：不同策略发车趟数允许变化，须同时比较运营成本；若使用不同车队规模，必须分开做实验。")

st.markdown('<div class="footer-text">⚠️ 研究型仿真，数据含地图估算和模型假设，不代表景区实测或实际优化效果。</div>', unsafe_allow_html=True)
