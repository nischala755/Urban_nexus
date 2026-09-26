"""Reproducible disturbances plus bounded numerical recovery estimates."""

from .domains import predictions
from .generator import stamp
from .schemas import Action, UrbanState
from .simulation import simulate_action


def run_stress(state, request):
    ids = {z.id for z in state.zones}
    if not set(request.affected_zones) <= ids:
        raise ValueError("Stress scenario contains unknown zones")
    # The named demo starts at t=0 and injects its disturbance after 10 minutes.
    no_action = Action(id="none", label="Normal operations", zone_id=state.zones[-1].id)
    normal = UrbanState.model_validate(simulate_action(state, no_action, 10, request.seed)["state"])
    disturbed = normal.model_copy(deep=True)
    disturbed.metadata.scenario = request.scenario
    disturbed.metadata.seed = request.seed
    severity = request.severity
    for z in disturbed.zones:
        if z.id not in request.affected_zones:
            continue
        if request.scenario in ["combined", "traffic_surge"]:
            z.traffic.arrival_vpm *= 1 + 0.55 * severity
        if request.scenario in ["combined", "water_surge"]:
            z.water.demand_m3h *= 1 + 0.60 * severity
        if request.scenario in ["combined", "energy_peak"]:
            z.energy.base_kw *= 1 + 0.65 * severity
        if request.scenario in ["combined", "waste_surge"]:
            z.waste.rate_pct_h *= 1 + 3.7 * severity
            z.waste.rate_std_pct_h *= 1 + severity
        if request.scenario == "pump_outage":
            z.water.pump_available = False
        z.energy.demand_kw = z.energy.base_kw + z.energy.flexible_kw + z.water.pump_kw
    if request.scenario == "vehicle_failure":
        disturbed.available_vehicles = 0
    stamp(disturbed)
    result = simulate_action(disturbed, no_action, request.duration_minutes, request.seed)
    alerts = predictions(disturbed, request.duration_minutes)
    time_to_degradation = next(
        (
            r["minute"]
            for r in result["series"]
            if r["reservoir_min_pct"] < 40
            or r["waste_fill_pct"] >= 100
            or r["traffic_delay_seconds"] > 60
            or r["energy_demand_kw"] > sum(z.energy.capacity_kw for z in state.zones) * 0.8
        ),
        None,
    )
    # Restore external demands after the finite disturbance, then simulate recovery.
    recovery_state = UrbanState.model_validate(result["state"])
    for z, reference in zip(recovery_state.zones, normal.zones):
        z.traffic.arrival_vpm = reference.traffic.arrival_vpm
        z.water.demand_m3h = reference.water.demand_m3h
        z.water.pump_available = reference.water.pump_available
        z.energy.base_kw = reference.energy.base_kw
        z.waste.rate_pct_h = reference.waste.rate_pct_h
    recovery = simulate_action(recovery_state, no_action, 120, request.seed)
    recovered = next(
        (
            r["minute"]
            for r in recovery["series"]
            if r["traffic_delay_seconds"] < 60 and r["reservoir_min_pct"] >= 40 and r["waste_fill_pct"] < 100
        ),
        None,
    )
    return {
        "scenario": request.model_dump(mode="json"),
        "baseline_state": normal,
        "stressed_state": disturbed,
        "projected_state": result["state"],
        "trajectory": result["series"],
        "degraded_kpis": result["kpis"],
        "time_to_degradation_minutes": time_to_degradation,
        "recovery_estimate_minutes": recovered,
        "recovery_note": "After disturbance ends; no waste collection. Null means no recovery within 120 minutes.",
        "affected_services": sorted({a["domain"] for p in alerts for a in p["alerts"]}),
        "predictions": alerts,
        "disturbance_at_minute": normal.elapsed_minutes,
    }
