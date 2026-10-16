"""景行智调：可复现的双向接驳离散事件仿真（研究用，非真实运营复刻）。

核心约束：全景区到达率仅计一次；乘客具有起讫站和方向；车辆按线路与
物理位置发车、行驶并折返；两条线路不跨线调车。A/B 共址站作为不同
线路候车队列，避免混乘造成的错误。返程使用同路反向距离是仿真假设。
"""

from collections import deque
from dataclasses import dataclass, field
import hashlib
import heapq
import itertools

import numpy as np

from data.routes import ROUTES
from data.segments import SEGMENTS
from data.stations import STATIONS
from data.vehicles import VEHICLE_TYPES
from core.optimizer import propose_departures


@dataclass
class Passenger:
    arrival_t: float
    destination_index: int


class Station:
    def __init__(self, sid, name):
        self.id = sid
        self.name = name
        self.queues = {1: deque(), -1: deque()}
        self.wait_records = []

    def add(self, passenger, direction):
        self.queues[direction].append(passenger)

    def board(self, capacity, t, direction):
        taken = []
        q = self.queues[direction]
        while q and len(taken) < capacity:
            passenger = q.popleft()
            self.wait_records.append(max(0.0, t - passenger.arrival_t))
            taken.append(passenger)
        return taken

    def size(self):
        return sum(len(q) for q in self.queues.values())


@dataclass
class Vehicle:
    id: str
    route_id: str
    capacity: int
    idx: int
    status: str = "idle"
    direction: int = 0
    onboard: list = field(default_factory=list)


def get_travel_time(frm, to, speed_kmh):
    """相同道路的反向路程视为相同：仅为情景建模假设。"""
    if speed_kmh <= 0:
        raise ValueError("speed_kmh 必须大于 0")
    for edge in SEGMENTS:
        if (edge["from"], edge["to"]) in ((frm, to), (to, frm)):
            d = edge["distance_km"]
            if d is None or d < 0:
                raise ValueError(f"缺少有效路段距离：{frm} -> {to}")
            return d / speed_kmh * 60
    raise ValueError(f"线路中不存在路段：{frm} -> {to}；不能静默使用假定的2分钟")


def _peak_factor(t_min, scenario_type, peak_multiplier, start_hour=8):
    clock = start_hour + t_min / 60.0
    if scenario_type == "上午高峰" and 8 <= clock < 11:
        return peak_multiplier
    if scenario_type == "下午高峰" and 14 <= clock < 17:
        return peak_multiplier
    return 1.0


def _outbound_probability(t_min, start_hour=8):
    """方向权重为示例假设，不属于景区实际OD调查。"""
    clock = start_hour + t_min / 60.0
    if 8 <= clock < 11:
        return 0.80
    if 14 <= clock < 17:
        return 0.20
    return 0.50


def _make_passenger(rng, route_id, direction, arrival_t):
    sids = ROUTES[route_id]["stations"]
    n = len(sids)
    if direction == 1:
        # 上午从起始接驳点上车的游客相对较多（假设）
        origins = np.arange(n - 1)
        weights = np.array([1.0 / (j + 1) ** 1.4 for j in origins])
    else:
        origins = np.arange(1, n)
        weights = np.array([1.0 / (n - j) ** 1.4 for j in origins])
    weights /= weights.sum()
    origin_idx = int(rng.choice(origins, p=weights))
    dests = np.arange(origin_idx + direction, n if direction == 1 else -1, direction)
    destination_idx = int(rng.choice(dests))
    return sids[origin_idx], Passenger(arrival_t, destination_idx)


def run_simulation(params, strategy="fixed", seed=42):
    """返回原Admin兼容字段，并补充客流守恒及调度成本指标。

    必填：duration_min, arrival_rate（全景区人/小时）
    可选：scenario_type（平峰/上午高峰/下午高峰）, peak_multiplier,
          fleet, fixed_interval, speed_kmh, queue_threshold,
          stop_dwell_min, turnaround_min, min_dispatch_gap_min,
          max_headway_min, demand_route_weights, vehicle_capacities。
    """
    if strategy not in {"fixed", "dynamic", "optimized"}:
        raise ValueError("strategy 必须是 fixed、dynamic 或 optimized")
    duration = float(params["duration_min"])
    arrival_rate = float(params["arrival_rate"])
    speed = float(params.get("speed_kmh", 15.0))
    interval = float(params.get("fixed_interval", 17.0))
    queue_threshold = int(params.get("queue_threshold", 20))
    peak_multiplier = float(params.get("peak_multiplier", 2.0))
    scenario_type = params.get("scenario_type", "平峰")
    dwell = float(params.get("stop_dwell_min", 0.5))
    turnaround = float(params.get("turnaround_min", 2.0))
    minimum_gap = float(params.get("min_dispatch_gap_min", 2.0))
    maximum_headway = float(params.get("max_headway_min", interval))
    start_hour = float(params.get("start_hour", 8))
    fleet = params.get("fleet", {"A": 5, "B": 3})
    if not (duration > 0 and arrival_rate >= 0 and speed > 0 and interval > 0):
        raise ValueError("时长/速度/间隔必须为正，客流率不得为负")
    if not (peak_multiplier >= 1 and queue_threshold >= 1 and dwell >= 0 and turnaround >= 0
            and minimum_gap > 0 and maximum_headway > 0):
        raise ValueError("高峰倍数、阈值及周转/发车参数不合法")
    if scenario_type not in {"平峰", "上午高峰", "下午高峰"}:
        raise ValueError("未知客流场景")

    route_ids = list(fleet)
    if not route_ids or any(rid not in ROUTES or int(fleet[rid]) < 0 for rid in route_ids):
        raise ValueError("fleet 中存在未知线路或非法数量")
    route_weights = params.get("demand_route_weights", {"A": 0.6, "B": 0.4})
    weights = np.array([float(route_weights.get(rid, 0.0)) for rid in route_ids])
    if (weights < 0).any() or weights.sum() <= 0:
        raise ValueError("demand_route_weights 无效")
    weights /= weights.sum()

    # A2/B1等是同一物理位置，但此处是分别等待A线/B线的候车队列；不互相挪客。
    stations = {sid: Station(sid, desc["name"]) for sid, desc in STATIONS.items()}
    vehicles = []
    vehicle_capacities = params.get("vehicle_capacities", {})
    for rid, count in fleet.items():
        route_sids = ROUTES[rid]["stations"]
        for i in range(int(count)):
            # 初始车辆在两个端点分布：一半向内、一半向外，仅为仿真假设。
            idx = 0 if i < (count + 1) // 2 else len(route_sids) - 1
            capacities = vehicle_capacities.get(rid, [])
            capacity = (int(capacities[i]) if i < len(capacities)
                        else int(VEHICLE_TYPES["中型"]["capacity"]))
            if capacity <= 0:
                raise ValueError("车辆容量必须为正")
            vehicles.append(Vehicle(f"{rid}-{i + 1:02d}", rid, capacity, idx))
    vmap = {v.id: v for v in vehicles}

    events = []
    counter = itertools.count()

    def push(t, kind, payload=None):
        # 用序号保证同一时刻多个事件不会触发无意义的对象比较。
        heapq.heappush(events, (float(t), next(counter), kind, payload))

    rng = np.random.default_rng(seed)
    demand_hash = hashlib.sha256()
    arrivals = 0
    # 逐分钟泊松采样，均值采用全景区到达率，不乘以站点个数。
    for minute in range(int(np.ceil(duration))):
        local_duration = min(1.0, duration - minute)
        if local_duration <= 0:
            break
        lam = arrival_rate / 60.0 * local_duration * _peak_factor(
            minute + 0.5 * local_duration, scenario_type, peak_multiplier, start_hour
        )
        for _ in range(int(rng.poisson(lam))):
            t = minute + rng.random() * local_duration
            route_id = str(rng.choice(route_ids, p=weights))
            direction = 1 if rng.random() < _outbound_probability(t, start_hour) else -1
            sid, passenger = _make_passenger(rng, route_id, direction, t)
            push(t, "arrival", (sid, direction, passenger))
            arrivals += 1
            demand_hash.update(f"{t:.7f}|{sid}|{direction}|{passenger.destination_index};".encode())

    if strategy == "fixed":
        for rid in route_ids:
            for direction in (1, -1):
                for step in range(int(np.ceil(duration / interval))):
                    t = step * interval
                    if t < duration:
                        push(t, "fixed_dispatch", (rid, direction))
    elif strategy == "dynamic":
        for minute in range(int(np.ceil(duration))):
            push(float(minute), "dynamic_check")
    else:
        decision_step = float(params.get("decision_interval_min", 5.0))
        if decision_step <= 0:
            raise ValueError("decision_interval_min 必须大于0")
        for t_opt in np.arange(0.0, duration, decision_step):
            push(float(t_opt), "optimized_check")

    boarded = 0
    alighted = 0
    departures = {rid: 0 for rid in route_ids}
    dispatch_log = []
    vehicle_busy_minutes = 0.0
    max_queues = {sid: 0 for sid in stations}
    last_departure = {(rid, d): -float("inf") for rid in route_ids for d in (1, -1)}

    def dispatch(t, rid, direction, vehicle_id=None):
        end_idx = 0 if direction == 1 else len(ROUTES[rid]["stations"]) - 1
        eligible = [v for v in vehicles if v.route_id == rid and v.status == "idle" and v.idx == end_idx
                    and (vehicle_id is None or v.id == vehicle_id)]
        if not eligible or t >= duration:
            return False
        vehicle = eligible[0]
        vehicle.status = "running"
        vehicle.direction = direction
        assert not vehicle.onboard
        last_departure[(rid, direction)] = t
        departures[rid] += 1
        dispatch_log.append({"time_min": round(t, 2), "vehicle_id": vehicle.id,
                             "route": rid, "direction": "去程" if direction == 1 else "返程"})
        push(t, "service", vehicle.id)
        return True

    def route_queue_info(rid, direction, now):
        sids = ROUTES[rid]["stations"]
        candidate_sids = sids[:-1] if direction == 1 else sids[1:]
        qlists = [stations[sid].queues[direction] for sid in candidate_sids]
        count = sum(len(q) for q in qlists)
        oldest = min((q[0].arrival_t for q in qlists if q), default=None)
        return count, (now - oldest if oldest is not None else 0.0)

    while events:
        t, _, kind, data = heapq.heappop(events)
        if t > duration:
            break
        if kind == "arrival":
            sid, direction, passenger = data
            stations[sid].add(passenger, direction)
            max_queues[sid] = max(max_queues[sid], stations[sid].size())

        elif kind == "fixed_dispatch":
            rid, direction = data
            dispatch(t, rid, direction)

        elif kind == "dynamic_check":
            for rid in route_ids:
                for direction in (1, -1):
                    count, longest_wait = route_queue_info(rid, direction, t)
                    enough_gap = t - last_departure[(rid, direction)] >= minimum_gap
                    if count > 0 and enough_gap and (count >= queue_threshold or longest_wait >= maximum_headway):
                        dispatch(t, rid, direction)

        elif kind == "optimized_check":
            # 预测层只读取当前已发生的客流及已安排的车辆运行事件。
            # 未来arrival虽然在离散事件堆中预生成，但优化器不会读取它们。
            chosen = propose_departures(
                now=t, stations=stations, vehicles=vehicles, events=events,
                last_departure=last_departure, params=params,
                route_weights=dict(zip(route_ids, weights.tolist()))
            )
            for vid in chosen:
                v = vmap[vid]
                direction = 1 if v.idx == 0 else -1
                if t - last_departure[(v.route_id, direction)] >= minimum_gap:
                    dispatch(t, v.route_id, direction, vehicle_id=vid)

        elif kind == "service":
            v = vmap[data]
            sid_list = ROUTES[v.route_id]["stations"]
            sid = sid_list[v.idx]
            still_onboard = []
            for person in v.onboard:
                if person.destination_index == v.idx:
                    alighted += 1
                else:
                    still_onboard.append(person)
            v.onboard = still_onboard
            next_idx = v.idx + v.direction
            if not (0 <= next_idx < len(sid_list)):
                if v.onboard:
                    raise AssertionError("抵达终点时仍有乘客未到目的地")
                v.status = "turnaround"
                push(t + turnaround, "ready", v.id)
            else:
                newly_boarded = stations[sid].board(v.capacity - len(v.onboard), t, v.direction)
                v.onboard.extend(newly_boarded)
                boarded += len(newly_boarded)
                tt = get_travel_time(sid, sid_list[next_idx], speed)
                trip_min = tt + dwell
                vehicle_busy_minutes += max(0.0, min(trip_min, duration - t))
                push(t + trip_min, "arrive", (v.id, next_idx))

        elif kind == "arrive":
            vid, next_idx = data
            v = vmap[vid]
            v.idx = next_idx
            push(t, "service", vid)

        elif kind == "ready":
            v = vmap[data]
            v.status = "idle"
            v.direction = 0

    waits = np.array([w for s in stations.values() for w in s.wait_records], dtype=float)
    remaining = {sid: st.size() for sid, st in stations.items()}
    unserved = sum(remaining.values())
    onboard_end = sum(len(v.onboard) for v in vehicles)
    # 对尚未上车旅客按观察窗口结束时的右删失等待进行统计，
    # 防止平均等待时间因“只服务少数乘客”而显得不合理地低。
    censored_wait = sum(max(0, duration - p.arrival_t) for st in stations.values()
                        for queue in st.queues.values() for p in queue)
    total_wait_person_min = float(waits.sum() + censored_wait)
    if arrivals != boarded + unserved or boarded != alighted + onboard_end:
        raise AssertionError(f"客流守恒失败：到达{arrivals}, 上车{boarded}, 候车{unserved}, 下车{alighted}, 在途{onboard_end}")

    return {
        "strategy": strategy,
        "avg_wait": float(waits.mean()) if waits.size else 0.0,
        "max_wait": float(waits.max()) if waits.size else 0.0,
        "p95_wait": float(np.percentile(waits, 95)) if waits.size else 0.0,
        "over_ratio": float((waits > 15).mean()) if waits.size else 0.0,
        "served": boarded,  # 与旧Admin字段兼容；准确含义为“已上车”
        "completed": alighted,
        "onboard_end": onboard_end,
        "total_arrivals": arrivals,
        "unserved": unserved,
        "total_wait_person_min": round(total_wait_person_min, 3),
        "avg_observed_wait_all": round(total_wait_person_min / arrivals, 3) if arrivals else 0.0,
        "service_rate": boarded / arrivals if arrivals else 1.0,
        "waits": waits.tolist(),
        "stations": remaining,
        "max_queues": max_queues,
        "departures": departures,
        "total_departures": sum(departures.values()),
        "vehicle_busy_minutes": round(vehicle_busy_minutes, 3),
        "dispatch_log": dispatch_log,
        "demand_signature": demand_hash.hexdigest()[:16],
        "seed": seed,
        "scenario_type": scenario_type,
        "params": {"duration_min": duration, "arrival_rate": arrival_rate,
                   "fleet": dict(fleet), "speed_kmh": speed,
                   "fixed_interval": interval, "queue_threshold": queue_threshold,
                   "peak_multiplier": peak_multiplier,
                   "decision_interval_min": params.get("decision_interval_min", 5),
                   "prediction_horizon_min": params.get("prediction_horizon_min", 45),
                   "beam_width": params.get("beam_width", 5),
                   "dispatch_penalty": params.get("dispatch_penalty", 15),
                   "fairness_weight": params.get("fairness_weight", 0.35),
                   "terminal_backlog_weight": params.get("terminal_backlog_weight", 1.0),
                   "stop_dwell_min": dwell, "turnaround_min": turnaround,
                   "vehicle_capacities": vehicle_capacities,
                   "demand_route_weights": dict(zip(route_ids, weights.tolist()))},
        "assumptions": "双向同路、车辆初始在两端分配、分线路候车、OD及客流时段权重均为仿真假设",
    }
