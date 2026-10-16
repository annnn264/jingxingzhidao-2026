import streamlit as st
from datetime import datetime
from core.simulation import run_simulation

st.title("🧠 Admin端 · 智能调度控制")
st.caption("仿真引擎调用入口 · 支持固定/阈值/滚动优化三种策略")

# ============================================================
# 1. 初始化状态
# ============================================================
if "fleet" not in st.session_state:
    st.session_state.fleet = {"A": 5, "B": 3}

if "scenario" not in st.session_state:
    st.session_state.scenario = {
        "type": "平峰",
        "arrival_rate": 120,
        "duration_min": 600,
        "seed": 42,
        "tidal": False,
        "disruption": False,
        "disruption_type": "客流突增"
    }
sc = st.session_state.scenario

# ============================================================
# 2. 界面配置
# ============================================================
st.markdown("> 20km/h是情景速度上限，不代表景区已核实限速。双向沿相同道路折返属于仿真假设。")

with st.container(border=True):
    st.subheader("🚌 车队配置")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.fleet["A"] = st.number_input("A线车辆数（辆）", 1, 20, st.session_state.fleet["A"])
    with col2:
        st.session_state.fleet["B"] = st.number_input("B线车辆数（辆）", 1, 20, st.session_state.fleet["B"])

with st.container(border=True):
    st.subheader("策略选择")
    strategy_display = st.radio(
        "选择调度策略",
        ["固定调度", "动态阈值调度", "滚动预测优化"],
        horizontal=True
    )
    strategy_map = {"固定调度": "fixed", "动态阈值调度": "dynamic", "滚动预测优化": "optimizer"}
    selected_strategy = strategy_map[strategy_display]

    if strategy_display == "滚动预测优化":
        with st.expander("⚙️ 优化算法参数（默认可用，必要时调整）", expanded=False):
            st.slider("决策间隔（分钟）", 5, 30, 10, 5)
            st.slider("预测窗口（分钟）", 30, 120, 60, 15)
            st.slider("束搜索宽度", 3, 20, 8, 1)

st.markdown("---")

# ============================================================
# 3. 运行仿真
# ============================================================
if st.button("▶️ 运行所选策略", type="primary", use_container_width=True):
    with st.spinner("仿真运行中，请稍候..."):
        params = {
            "duration_min": sc["duration_min"],
            "arrival_rate": sc["arrival_rate"],
            "fleet": st.session_state.fleet,
            "fixed_interval": 17,
            "speed_kmh": 15,
            "queue_threshold": 20,
            "peak_multiplier": 1.0,
        }
        
        # 注：若 optimizer.py 未实现，这里强制回退到 dynamic，避免报错
        if selected_strategy == "optimizer":
            st.info("优化器尚未接入，已自动回退为动态阈值调度。")
            result = run_simulation(params, strategy="dynamic", seed=sc["seed"])
        else:
            result = run_simulation(params, strategy=selected_strategy, seed=sc["seed"])
            
        st.session_state["last_result"] = result
        st.session_state["last_run_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if "last_result" in st.session_state:
    st.success("✅ 仿真已完成")
    st.button("📊 同场景对比三种策略", use_container_width=True)

    st.markdown("---")
    r = st.session_state["last_result"]

    # 直接从引擎返回的字典中提取统计指标
    avg_wait = r.get("avg_wait", 0.0)
    max_wait = r.get("max_wait", 0.0)
    total_arrivals = r.get("total_arrivals", 0)
    boarded = r.get("boarded", 0)
    queue_end = r.get("queue_end", 0)
    total_trips = r.get("total_trips", 0)
    service_rate = r.get("service_rate", 0.0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("全体到达者的观测候车均值", f"{avg_wait:.1f} min")
    c2.metric("已上车游客P95候车", f"{max_wait:.1f} min") # 暂时用 max_wait 代替
    c3.metric("未上车人数", f"{queue_end} 人")
    c4.metric("上车服务率", f"{service_rate:.1f}%")

    st.markdown("---")
    
    # 动态拼接场景文案
    scenario_text = f"**【{sc.get('type', '平峰')}】场景**"
    if sc.get("tidal", False):
        scenario_text += " + **节假日潮汐客流**"
    if sc.get("disruption", False):
        scenario_text += f" + **突发情况：{sc.get('disruption_type', '客流突增')}**"

    st.markdown(f"""
    #### 📋 仿真结果复原
    
    **场景复现**：基于您设置的 {scenario_text}  
    **运力配置**：A线 {st.session_state.fleet['A']} 辆，B线 {st.session_state.fleet['B']} 辆。  
    **运营成果**：共到达 **{total_arrivals}** 人，成功上车 **{boarded}** 人，期末仍在排队 **{queue_end}** 人；总发车 **{total_trips}** 趟。  
    **服务指标**：上车服务率 **{service_rate:.1f}%**。  
    """)

    st.markdown("*注：已观察候车均值对未上车游客统计到仿真截止时为止的等待，属于损失下界；不是所有游客最终完整候车时长。*")

else:
    st.info("👈 请点击上方按钮开始仿真。")

st.markdown("---")
st.warning("⚠️ 研究型仿真，数据含地图估算和模型假设，不代表景区实测或实际优化效果。")