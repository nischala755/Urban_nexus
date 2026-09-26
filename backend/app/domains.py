"""Inspectable reference equations; all coefficients are synthetic assumptions."""
import math
import statistics
from statistics import NormalDist

MODEL_VERSIONS = {"traffic": "fluid-queue/1.0", "water": "reservoir-p/1.0",
                  "energy": "load-balance/1.0", "waste": "normal-rate/1.0",
                  "optimizer": "enumeration-lexicographic/1.0"}
PUMP_KWH_PER_M3 = 0.6
EV_KWH_PER_KM = 1.2
EV_IDLE_KWH_PER_MIN = 0.025
GRID_KG_PER_KWH = 0.7


def water_step(volume, demand, capacity, pump_capacity, available, adjustment=0, dt_minutes=1):
    flow = min(pump_capacity, max(0, demand + 0.5 * (0.65 * capacity - volume) + adjustment))
    if not available:
        flow = 0
    raw = volume + (flow - demand) * dt_minutes / 60
    return {"volume_m3": min(capacity, max(0, raw)), "pump_flow_m3h": flow,
            "pump_kw": flow * PUMP_KWH_PER_M3, "unserved_m3": max(0, -raw),
            "spill_m3": max(0, raw - capacity)}


def traffic_step(queue, arrival_vpm, green_seconds, extra_pcu_vpm=0, dt_minutes=1):
    service = green_seconds  # 60-second cycle, 1 vehicle per green second.
    arrivals = arrival_vpm + extra_pcu_vpm
    next_queue = max(0, queue + (arrivals - service) * dt_minutes)
    density = arrivals / max(service, 1)
    delay = 8 + 12 * density / max(0.15, 1 - min(0.95, density)) + next_queue / max(arrivals, 1) * 60
    speed = 40 / (1 + delay / 60)
    return {"queue_vehicles": next_queue, "density": density, "delay_seconds": delay,
            "average_speed_kph": speed, "vehicle_count": arrivals * 5 + next_queue}


def overflow_risk(fill, rate, std, horizon_minutes, collection_minute=None):
    """P(any overflow) for one shared uncertain constant rate and complete emptying.

    Overflow before collection is not erased by a later successful collection.
    The event is R >= min((100-fill)/time_to_collection, 100/time_after_collection).
    """
    if fill >= 100:
        return 1.0
    hours = horizon_minutes / 60
    if hours <= 0:
        return 0.0
    if collection_minute is None or collection_minute > horizon_minutes:
        threshold = (100 - fill) / hours
    else:
        before = max(0, collection_minute) / 60
        after = max(0, horizon_minutes - collection_minute) / 60
        threshold = min((100 - fill) / before if before else math.inf,
                        100 / after if after else math.inf)
    if std <= 0:
        return float(rate >= threshold)
    return max(0.0, min(1.0, 1 - NormalDist(rate, std).cdf(threshold)))


def _predict(values, method):
    if method == "persistence":
        return values[-1]
    window = values[-6:]
    n = len(window)
    mean_x = (n - 1) / 2
    mean_y = statistics.mean(window)
    slope = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(window)) / sum(
        (i - mean_x) ** 2 for i in range(n))
    return max(0, mean_y + slope * (n - mean_x))


def forecast(values):
    if len(values) < 3 or not all(math.isfinite(v) and v >= 0 for v in values):
        raise ValueError("Forecast requires at least three finite nonnegative observations")
    errors = {}
    for method in ["persistence", "linear_trend"]:
        errors[method] = [abs(values[i] - _predict(values[:i], method)) for i in range(2, len(values))]
    method = min(errors, key=lambda key: statistics.mean(errors[key]))
    estimate = _predict(values, method)
    radius = max(errors[method])
    return {"predicted": estimate, "method": method,
            "validation_mae": statistics.mean(errors[method]),
            "baseline_mae": statistics.mean(errors["persistence"]),
            "interval": [max(0, estimate - radius), estimate + radius],
            "interval_kind": "held-out absolute residual envelope; not calibrated",
            "low_confidence": radius > max(1, estimate * 0.2)}


def anomaly_score(history, current):
    center = statistics.median(history)
    mad = statistics.median(abs(x - center) for x in history)
    return abs(current - center) / max(1, 1.4826 * mad)


def energy_schedule(base_kw, tariffs, flexible_kwh, capacity_kw):
    """Place a one-hour indivisible municipal task inside a supplied operating window."""
    if not base_kw or len(base_kw) != len(tariffs):
        raise ValueError("Equal nonempty demand and tariff windows required")
    candidates = []
    for slot in range(len(base_kw)):
        loads = [flexible_kwh if i == slot else 0 for i in range(len(base_kw))]
        # Existing exogenous peaks do not prevent task placement in a different safe slot.
        if base_kw[slot] + flexible_kwh > capacity_kw:
            continue
        total = [base + load for base, load in zip(base_kw, loads)]
        cost = sum(load * tariff for load, tariff in zip(loads, tariffs))
        objective = cost + 0.1 * max(total) + 2 * slot
        candidates.append({"slot": slot, "load_kw": loads, "objective": objective,
                           "cost_inr": cost, "feasible": True})
    return min(candidates, key=lambda c: c["objective"]) if candidates else {"feasible": False}


def predictions(state, horizon_minutes=60):
    result = []
    for z in state.zones:
        energy = forecast(z.energy.history + [z.energy.demand_kw])
        water = forecast(z.water.history + [z.water.demand_m3h])
        traffic = forecast(z.traffic.history + [z.traffic.arrival_vpm])
        risk = overflow_risk(z.waste.fill_pct, z.waste.rate_pct_h,
                             z.waste.rate_std_pct_h, horizon_minutes)
        score = anomaly_score(z.water.history, z.water.demand_m3h)
        alerts = []
        if traffic["predicted"] / z.traffic.green_seconds > 0.85:
            alerts.append({"domain": "traffic", "message": "Congestion risk: arrival rate approaches service"})
        if energy["predicted"] > 0.80 * z.energy.capacity_kw:
            alerts.append({"domain": "energy", "message": "Approaching feeder peak; consider flexible-load scheduling"})
        if score > 3:
            alerts.append({"domain": "water", "message": f"Abnormal consumption pattern — investigate {z.id}"})
        if risk >= 0.10:
            alerts.append({"domain": "waste", "message": "Overflow risk exceeds 10% model threshold"})
        result.append({"zone_id": z.id, "energy": energy, "water": water, "traffic": traffic,
                       "waste_overflow_probability": risk, "water_anomaly_score": score,
                       "alerts": alerts, "horizon_minutes": horizon_minutes})
    return result
