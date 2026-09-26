"""Pure coupled counterfactual; operational truth comes from these equations."""

import math
import time
from datetime import timedelta

from .domains import (
    EV_IDLE_KWH_PER_MIN,
    EV_KWH_PER_KM,
    GRID_KG_PER_KWH,
    MODEL_VERSIONS,
    overflow_risk,
    traffic_step,
    water_step,
)
from .generator import stamp
from .network import route_edges
from .schemas import Action, UrbanState

DEPENDENCIES = [
    {
        "from": "water_pumping",
        "to": "electricity",
        "formula": "pump_flow_m3h * 0.6",
        "unit": "kW",
        "assumption": "Constant specific energy 0.6 kWh/m3",
        "provenance": "reservoir-p/1.0",
    },
    {
        "from": "waste_collection",
        "to": "traffic_load",
        "formula": "vehicles * 2.5 * 30 / road_capacity_vpm",
        "unit": "PCU/min",
        "assumption": "Truck equivalent occupancy during route",
        "provenance": "fluid-queue/1.0",
    },
    {
        "from": "distance_and_delay",
        "to": "collection_energy",
        "formula": "km * 1.2 + idle_minutes * 0.025",
        "unit": "kWh",
        "assumption": "EV fleet; charging allocated within horizon",
        "provenance": "load-balance/1.0",
    },
    {
        "from": "grid_electricity",
        "to": "emissions_proxy",
        "formula": "additional_kwh * 0.7",
        "unit": "kgCO2e",
        "assumption": "Illustrative grid factor, not measured emissions",
        "provenance": "load-balance/1.0",
    },
]


def zone_by_id(state, zone_id):
    zone = next((z for z in state.zones if z.id == zone_id), None)
    if zone is None:
        raise ValueError(f"Unknown zone {zone_id}")
    return zone


def route_metrics(state, action):
    if not action.vehicles:
        if action.route:
            raise ValueError("A route requires a vehicle")
        return {"distance_km": 0.0, "arrival_minutes": 0, "duration_minutes": 0.0, "edges": []}
    if len(action.route) < 2 or action.route[0] != "DEPOT" or action.route[-1] != action.zone_id:
        raise ValueError("Collection route must start at DEPOT and end at the target zone")
    if len(set(action.route)) != len(action.route):
        raise ValueError("Route must be a simple path")
    edges = route_edges(action.route)
    travel = 0
    for edge in edges:
        z = zone_by_id(state, edge["zone"])
        traffic = traffic_step(z.traffic.queue_vehicles, z.traffic.arrival_vpm, z.traffic.green_seconds)
        travel += edge["km"] / max(5, traffic["average_speed_kph"]) * 60
    return {
        "distance_km": 2 * sum(e["km"] for e in edges),
        "arrival_minutes": math.ceil(travel),
        "duration_minutes": 2 * travel + 8,
        "edges": edges,
    }


def instant_kpis(state, zone_id="Z04", horizon_minutes=60):
    z = zone_by_id(state, zone_id)
    return {
        "traffic_delay_seconds": sum(z.traffic.delay_seconds for z in state.zones) / len(state.zones),
        "average_speed_kph": sum(z.traffic.average_speed_kph for z in state.zones) / len(state.zones),
        "queue_vehicles": sum(z.traffic.queue_vehicles for z in state.zones),
        "energy_demand_kw": sum(z.energy.demand_kw for z in state.zones),
        "net_grid_kw": sum(max(0, z.energy.demand_kw - z.energy.renewable_kw) for z in state.zones),
        "reservoir_min_pct": min(z.water.reservoir_m3 / z.water.capacity_m3 * 100 for z in state.zones),
        "pump_kw": sum(z.water.pump_kw for z in state.zones),
        "waste_fill_pct": z.waste.fill_pct,
        "overflow_probability": overflow_risk(
            z.waste.fill_pct, z.waste.rate_pct_h, z.waste.rate_std_pct_h, horizon_minutes
        ),
    }


def simulate_action(baseline_state: UrbanState, action: Action, horizon_minutes: int = 60, seed: int = 42):
    if not 1 <= horizon_minutes <= 180:
        raise ValueError("Simulation horizon must be 1..180 minutes")
    start = time.perf_counter()
    state = baseline_state.model_copy(deep=True)
    target = zone_by_id(state, action.zone_id)
    original = zone_by_id(baseline_state, action.zone_id)
    route = route_metrics(state, action)
    arrival = route["arrival_minutes"] if action.vehicles else None
    required_volume = (
        (original.waste.fill_pct + original.waste.rate_pct_h * (arrival or 0) / 60)
        / 100
        * original.waste.bin_capacity_m3
    )
    physical = {
        "vehicle_availability": {"actual": action.vehicles, "allowed": state.available_vehicles},
        "vehicle_capacity_m3": {
            "actual": required_volume if action.vehicles else 0,
            "allowed": action.vehicles * state.vehicle_capacity_m3,
        },
        "collection_within_horizon": {"actual": arrival or 0, "allowed": horizon_minutes},
        "route_completion_within_horizon": {"actual": route["duration_minutes"], "allowed": horizon_minutes},
        "green_seconds_max": {
            "actual": target.traffic.green_seconds + action.green_delta_seconds,
            "allowed": 45,
        },
        "green_seconds_min": {
            "actual": target.traffic.green_seconds + action.green_delta_seconds,
            "allowed": 15,
            "minimum": True,
        },
        "flexible_load_kw": {"actual": action.load_shift_kw, "allowed": target.energy.flexible_kw},
    }
    can_collect = (
        action.vehicles > 0
        and action.vehicles <= state.available_vehicles
        and required_volume <= action.vehicles * state.vehicle_capacity_m3
        and arrival <= horizon_minutes
    )
    green = min(45, max(15, target.traffic.green_seconds + action.green_delta_seconds))
    target.traffic.green_seconds = green
    shift = min(action.load_shift_kw, target.energy.flexible_kw)
    ev_kwh = action.vehicles * (
        route["distance_km"] * EV_KWH_PER_KM + route["duration_minutes"] * EV_IDLE_KWH_PER_MIN
    )
    charge_kw = ev_kwh * 60 / horizon_minutes
    rows = []
    min_reservoir = min(z.water.reservoir_m3 / z.water.capacity_m3 * 100 for z in state.zones)
    peak_feeder_ratio = max(z.energy.demand_kw / z.energy.capacity_kw for z in state.zones)
    unserved = 0.0
    repaid_kwh = 0.0
    for minute in range(1, horizon_minutes + 1):
        for z in state.zones:
            water = water_step(
                z.water.reservoir_m3,
                z.water.demand_m3h,
                z.water.capacity_m3,
                z.water.pump_capacity_m3h,
                z.water.pump_available,
                action.pump_adjustment_m3h if z.id == action.zone_id else 0,
            )
            z.water.reservoir_m3 = water["volume_m3"]
            z.water.pump_flow_m3h = water["pump_flow_m3h"]
            z.water.pump_kw = water["pump_kw"]
            unserved += water["unserved_m3"]
            extra = sum(
                action.vehicles * 2.5 * 30 / e["capacity_vpm"]
                for e in route["edges"]
                if e["zone"] == z.id and minute <= route["duration_minutes"]
            )
            traffic = traffic_step(
                z.traffic.queue_vehicles, z.traffic.arrival_vpm, z.traffic.green_seconds, extra
            )
            for key, value in traffic.items():
                setattr(z.traffic, key, value)
            repayment_kw = 0.0
            if z.energy.deferred_kwh > 0:
                remaining = max(1, z.energy.recovery_minutes_remaining)
                repayment_kw = z.energy.deferred_kwh * 60 / remaining
                repaid_kwh += repayment_kw / 60
                z.energy.deferred_kwh = max(0, z.energy.deferred_kwh - repayment_kw / 60)
                z.energy.recovery_minutes_remaining = max(0, remaining - 1)
            z.energy.demand_kw = (
                z.energy.base_kw
                + z.energy.flexible_kw
                + z.water.pump_kw
                + repayment_kw
                - (shift if z.id == action.zone_id else 0)
                + (charge_kw if z.id == action.zone_id else 0)
            )
            z.waste.fill_pct = min(300, z.waste.fill_pct + z.waste.rate_pct_h / 60)
            if z.id == action.zone_id and can_collect and minute == max(1, arrival):
                z.waste.fill_pct = 0
        row = instant_kpis(state, action.zone_id, 0)
        row["minute"] = minute
        rows.append(row)
        min_reservoir = min(min_reservoir, row["reservoir_min_pct"])
        peak_feeder_ratio = max(
            peak_feeder_ratio, max(z.energy.demand_kw / z.energy.capacity_kw for z in state.zones)
        )
    state.elapsed_minutes += horizon_minutes
    state.timestamp += timedelta(minutes=horizon_minutes)
    target.energy.deferred_kwh += shift * horizon_minutes / 60
    if shift:
        target.energy.recovery_minutes_remaining = 120
    # At the horizon boundary the action ends, normal flexible work resumes and
    # its deferred energy enters the explicit two-hour repayment window.
    for z in state.zones:
        recovery_kw = z.energy.deferred_kwh * 60 / max(1, z.energy.recovery_minutes_remaining)
        z.energy.demand_kw = z.energy.base_kw + z.energy.flexible_kw + z.water.pump_kw + recovery_kw
    stamp(state)
    risk = overflow_risk(
        original.waste.fill_pct,
        original.waste.rate_pct_h,
        original.waste.rate_std_pct_h,
        horizon_minutes,
        arrival if can_collect else None,
    )
    kpis = instant_kpis(state, action.zone_id, 0)
    for key in ["traffic_delay_seconds", "average_speed_kph", "energy_demand_kw", "net_grid_kw", "pump_kw"]:
        kpis[key] = sum(r[key] for r in rows) / len(rows)
    kpis.update(
        {
            "overflow_probability": risk,
            "reservoir_min_pct": min_reservoir,
            "energy_peak_kw": max(r["energy_demand_kw"] for r in rows),
            "energy_kwh": sum(r["net_grid_kw"] for r in rows) / 60,
            "renewable_utilization_pct": 100
            * sum(min(z.energy.renewable_kw, z.energy.demand_kw) for z in state.zones)
            / max(1, sum(z.energy.renewable_kw for z in state.zones)),
            "distance_km": route["distance_km"] * action.vehicles,
            "travel_time_minutes": route["duration_minutes"],
            "response_minutes": arrival or 0,
            "collection_energy_kwh": ev_kwh,
            "deferred_energy_kwh": shift * horizon_minutes / 60,
            "repaid_energy_kwh": repaid_kwh,
            "cost_inr": action.vehicles * (700 + route["distance_km"] * 35 + route["duration_minutes"] * 8)
            + abs(action.pump_adjustment_m3h) * 2
            + shift * 3
            + abs(action.green_delta_seconds) * 10,
            "emissions_proxy_kg": ev_kwh * GRID_KG_PER_KWH,
            "energy_cost_proxy_inr": sum(r["net_grid_kw"] for r in rows) / 60 * 8,
        }
    )
    physical["feeder_capacity_ratio"] = {"actual": peak_feeder_ratio, "allowed": 1}
    physical["unserved_water_m3"] = {"actual": unserved, "allowed": 0}
    # A shifted flexible task must fit a known two-hour recovery window after this horizon.
    physical["deferred_load_recovery_kw"] = {
        "actual": original.energy.base_kw
        + original.water.pump_capacity_m3h * 0.6
        + original.energy.flexible_kw
        + target.energy.deferred_kwh / 2,
        "allowed": original.energy.capacity_kw,
    }
    uncertainty = {
        "kind": "assumed normal fill-rate sensitivity; not field calibrated",
        "rate_std_pct_h": original.waste.rate_std_pct_h,
        "fill_90pct_interval": [
            max(0, target.waste.fill_pct - 1.645 * original.waste.rate_std_pct_h * horizon_minutes / 60),
            target.waste.fill_pct + 1.645 * original.waste.rate_std_pct_h * horizon_minutes / 60,
        ],
        "low_confidence": original.waste.rate_std_pct_h > 0.3 * max(1, original.waste.rate_pct_h),
    }
    return {
        "state": state.model_dump(mode="json"),
        "kpis": kpis,
        "series": rows,
        "physical_constraints": physical,
        "model_versions": MODEL_VERSIONS,
        "seed": seed,
        "horizon_minutes": horizon_minutes,
        "runtime_ms": (time.perf_counter() - start) * 1000,
        "affected_zones": sorted(set([action.zone_id] + [e["zone"] for e in route["edges"]])),
        "assumptions": state.metadata.assumptions
        + [
            "Exogenous rates constant within horizon",
            "Deferred flexible work completes within two-hour recovery window",
        ],
        "uncertainty": uncertainty,
    }


def calculate_ripple(baseline, simulated, action, dependency_graph=None):
    before, after = baseline["kpis"], simulated["kpis"]
    deltas = {k: after[k] - before[k] for k in before}
    return {
        "deltas": deltas,
        "dependencies": dependency_graph or DEPENDENCIES,
        "contributions": [
            {
                "cause": "Pump operation",
                "effect": "Municipal electricity",
                "value": deltas["pump_kw"],
                "unit": "kW",
            },
            {
                "cause": "Collection distance + route delay",
                "effect": "EV charging",
                "value": after["collection_energy_kwh"],
                "unit": "kWh",
            },
            {
                "cause": "Collection vehicle road occupancy",
                "effect": "Mean traffic delay",
                "value": deltas["traffic_delay_seconds"],
                "unit": "seconds",
            },
            {
                "cause": "Additional collection electricity",
                "effect": "Grid emissions proxy",
                "value": after["emissions_proxy_kg"],
                "unit": "kgCO2e",
            },
        ],
        "action_id": action.id,
    }
