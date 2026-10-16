import heapq
import numpy as np
from collections import deque

from data.stations import STATIONS, SHARED
from data.routes import ROUTES
from data.segments import SEGMENTS
from data.vehicles import VEHICLE_TYPES


class Station:
    def __init__(self, sid, name):
        self.id = sid
        self.name = name
        self.queue = deque()
        self.wait_records = []

    def add(self, t):
        self.queue.append(t)

    def board(self, capacity, t):
        n = 0
        while self.queue and n < capacity:
            self.wait_records.append(t - self.queue.popleft())
            n += 1
        return n

    def size(self):
        return len(self.queue)


class Vehicle:
    def __init__(self, vid, route_id, capacity):
        self.id = vid
        self.route_id = route_id
        self.capacity = capacity
        self.idx = 0
        self.onboard = 0
        self.status = "idle"

    def current(self):
        return ROUTES[self.route_id]["stations"][self.idx]

    def next_station(self):
        i = self.idx + 1
        stations = ROUTES[self.route_id]["stations"]
        return stations[i] if i < len(stations) else None


def get_travel_time(frm, to, speed_kmh):
    for e in SEGMENTS:
        if e["from"] == frm and e["to"] == to:
            if e["distance_km"] is None:
                return 3.0
            return e["distance_km"] / speed_kmh * 60
    return 3.0


def run_simulation(params, strategy="fixed", seed=42):
    rng = np.random.default_rng(seed)

    stations = {sid: Station(sid, s["name"]) for sid, s in STATIONS.items()}

    fleet = params.get("fleet", {"A": 5, "B": 3})
    speed = params.get("speed_kmh", 15)
    capacity = VEHICLE_TYPES["中型"]["capacity"]

    vehicles = []
    for rid, cnt in fleet.items():
        for i in range(cnt):
            vehicles.append(Vehicle(f"{rid}-{i+1:02d}", rid, capacity))

    duration = params["duration_min"]
    rate_per_min = params["arrival_rate"] / 60
    peak_mul = params.get("peak_multiplier", 1.0)

    events = []
    total_arrived = 0  # 统计总到达人数

    for sid in STATIONS:
        n = int(rate_per_min * duration * peak_mul)
        if n <= 0:
            continue
        times = rng.uniform(0, duration, n)
        total_arrived += n
        for t in times:
            heapq.heappush(events, (t, "arrival", sid))

    if strategy == "fixed":
        interval = params["fixed_interval"]
        t = 0
        while t < duration:
            for v in vehicles:
                if v.status == "idle":
                    heapq.heappush(events, (t, "dispatch", v.id))
                    break
            t += interval

    if strategy == "dynamic":
        for t in np.arange(1, duration, 1.0):
            heapq.heappush(events, (t, "check", None))

    vmap = {v.id: v for v in vehicles}
    total_trips = 0  # 统计发车总趟数

    while events:
        t, etype, data = heapq.heappop(events)
        if t > duration:
            break

        if etype == "arrival":
            stations[data].add(t)

        elif etype == "dispatch":
            v = vmap[data]
            if v.status == "idle":
                v.status = "running"
                total_trips += 1  # 成功发车，计数+1
                heapq.heappush(events, (t + 1, "move", v.id))

        elif etype == "move":
            v = vmap[data]
            sid = v.current()

            board_sid = SHARED.get(sid, sid)
            boarded = stations[board_sid].board(v.capacity - v.onboard, t)
            v.onboard += boarded

            nxt = v.next_station()
            if nxt is None:
                v.onboard = 0
                v.idx = 0
                v.status = "idle"
                continue

            tt = get_travel_time(sid, nxt, speed)
            v.idx += 1
            heapq.heappush(events, (t + tt, "move", v.id))

        elif etype == "check":
            threshold = params.get("queue_threshold", 20)
            for sid, st in stations.items():
                if st.size() >= threshold:
                    for v in vehicles:
                        if v.status == "idle":
                            v.status = "running"
                            total_trips += 1
                            heapq.heappush(events, (t + 1, "move", v.id))
                            break

    all_waits = []
    total_boarded = 0
    for st in stations.values():
        all_waits.extend(st.wait_records)
        total_boarded += len(st.wait_records)

    queue_end = sum(st.size() for st in stations.values())
    service_rate = (total_boarded / total_arrived * 100) if total_arrived > 0 else 0.0

    if not all_waits:
        return {
            "strategy": strategy,
            "avg_wait": 0.0,
            "max_wait": 0.0,
            "over_ratio": 0.0,
            "served": 0,
            "waits": [],
            "total_arrivals": total_arrived,
            "boarded": total_boarded,
            "queue_end": queue_end,
            "total_trips": total_trips,
            "service_rate": service_rate,
            "stations": {sid: st.size() for sid, st in stations.items()},
        }

    waits = np.array(all_waits)
    return {
        "strategy": strategy,
        "avg_wait": float(waits.mean()),
        "max_wait": float(waits.max()),
        "over_ratio": float((waits > 15).mean()),
        "served": int(len(waits)),
        "waits": waits.tolist(),
        "total_arrivals": total_arrived,
        "boarded": total_boarded,
        "queue_end": queue_end,
        "total_trips": total_trips,
        "service_rate": service_rate,
        "stations": {sid: st.size() for sid, st in stations.items()},
    }