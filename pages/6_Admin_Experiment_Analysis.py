import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

st.title("📊 Admin端 · 实验效果分析")

if "experiments" not in st.session_state:
    st.session_state.experiments = []

col1, col2 = st.columns([1, 3])

with col1:
    if st.button("📝 保存当前实验", type="primary", use_container_width=True):
        if "result" in st.session_state:
            r = st.session_state["result"]
            st.session_state.experiments.append({
                "编号": f"E{len(st.session_state.experiments)+1:03d}",
                "时间": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "策略": r["strategy"],
                "平均等待": round(r["avg_wait"], 1),
                "最大等待": round(r["max_wait"], 1),
                "完成运输": r["served"],
            })
            st.success("已保存")
        else:
            st.warning("请先运行仿真")

    if st.button("🗑️ 清空", use_container_width=True):
        st.session_state.experiments = []
        st.rerun()

with col2:
    if st.session_state.experiments:
        df = pd.DataFrame(st.session_state.experiments)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("⬇️ 导出 CSV",
                           df.to_csv(index=False).encode("utf-8-sig"),
                           "experiments.csv", "text/csv",
                           use_container_width=True)
    else:
        st.info("暂无实验记录")

if st.session_state.experiments:
    with st.container(border=True):
        st.subheader("📊 实验对比")
        df = pd.DataFrame(st.session_state.experiments)
        fig = go.Figure()
        fig.add_trace(go.Bar(name="平均等待", x=df["编号"],
                              y=df["平均等待"], marker_color="#5B8FF9"))
        fig.add_trace(go.Bar(name="最大等待", x=df["编号"],
                              y=df["最大等待"], marker_color="#F6BD16"))
        fig.update_layout(barmode="group", height=350, yaxis_title="分钟")
        st.plotly_chart(fig, use_container_width=True)

st.markdown('<div class="footer-text">⚠️ 所有结果由程序生成，不代表景区实测。</div>', unsafe_allow_html=True)