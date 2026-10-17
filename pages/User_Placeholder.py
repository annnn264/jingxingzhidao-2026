"""User 队友页面的接入位置；演示读同次仿真结果，不虚构ETA。"""
import streamlit as st
import pandas as pd

st.title("📍 User 游客端 · 接入占位")
st.warning("正式游客交互页面尚未合并。本页仅验证同一网站能够访问Admin端本轮仿真数据，"
           "不是已完成的游客服务系统。")
result = st.session_state.get("last_result")
if result is None:
    st.info("请先在顶部的「Admin 管理端 → 智能调度」运行一次仿真，然后再返回本页。")
else:
    st.success(f"已读取当前浏览器会话中的Admin仿真：{result['run_id']}")
    st.caption("数据只反映所选模拟场景；不是现实车辆的实时GPS位置。")
    states = pd.DataFrame(result["station_state"])
    if not states.empty:
        latest_time = states["time_min"].max()
        latest = states[states["time_min"] == latest_time]
        st.subheader(f"站点队列预览（仿真时刻 {latest_time:g} 分钟）")
        st.dataframe(latest[["route_id", "route_station_seq", "station_id",
                             "direction", "queue_length"]],
                     hide_index=True, use_container_width=True)
    st.caption("正式版需由User端队友补充起终点选择、OD寻路和ETA等功能；"
               "不同设备访问时不能使用session_state传递数据，需再接入共享数据库/API。")
