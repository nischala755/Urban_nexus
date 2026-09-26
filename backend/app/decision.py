"""Exhaustive small candidate set: hard feasibility first, magnitude before preference."""

from collections import Counter

from .network import paths_to
from .schemas import Action, DecisionRequest, ImpactBudget, Weights
from .simulation import calculate_ripple, simulate_action, zone_by_id


def generate_candidates(state, zone_id="Z04"):
    zone_by_id(state, zone_id)
    actions = [Action(id="no-action", label="Continue current operations", zone_id=zone_id)]
    for index, route in enumerate(paths_to(zone_id)):
        for vehicles in [1, 2]:
            actions.append(
                Action(
                    id=f"collect-{index}-{vehicles}",
                    label=f"{vehicles} EV{'s' if vehicles > 1 else ''} via {' → '.join(route[1:])}",
                    kind="waste",
                    zone_id=zone_id,
                    route=route,
                    vehicles=vehicles,
                )
            )
    return actions


def domain_candidates(state, zone_id):
    zone_by_id(state, zone_id)
    return (
        [
            Action(
                id=f"shift-{kw}",
                label=f"Defer {kw} kW flexible load",
                kind="energy",
                zone_id=zone_id,
                load_shift_kw=kw,
            )
            for kw in [20, 40, 60]
        ]
        + [
            Action(
                id=f"pump-{flow}",
                label=f"Adjust pump by {flow:+} m³/h",
                kind="water",
                zone_id=zone_id,
                pump_adjustment_m3h=flow,
            )
            for flow in [-50, 25, 50]
        ]
        + [
            Action(
                id=f"signal-{seconds}",
                label=f"Add {seconds} seconds green",
                kind="traffic",
                zone_id=zone_id,
                green_delta_seconds=seconds,
            )
            for seconds in [5, 10, 15]
        ]
    )


def percentage_delta(before, after):
    return (after - before) / max(abs(before), 1e-6) * 100


def check_impact_budget(baseline, simulated, budget: ImpactBudget):
    after = simulated["kpis"]
    rows = []

    def peak_delta(key):
        baseline_series, action_series = baseline["series"], simulated["series"]
        if len(baseline_series) != len(action_series) or not baseline_series:
            raise ValueError("Budget comparison requires equal nonempty time horizons")
        return max(percentage_delta(b[key], a[key]) for b, a in zip(baseline_series, action_series))

    def add(name, actual, allowed, unit, minimum=False, strict=False):
        margin = actual - allowed if minimum else allowed - actual
        passed = margin > 0 if strict else margin >= -1e-9
        rows.append(
            {
                "name": name,
                "actual": actual,
                "allowed": allowed,
                "unit": unit,
                "margin": margin,
                "status": "PASS" if passed else "FAIL",
                "minimum": minimum,
                "strict": strict,
            }
        )

    add(
        "traffic_delay",
        peak_delta("traffic_delay_seconds"),
        budget.traffic_delay_max_delta,
        "%",
    )
    add(
        "energy_demand",
        peak_delta("energy_demand_kw"),
        budget.energy_demand_max_delta,
        "%",
    )
    add("reservoir", after["reservoir_min_pct"], budget.water_reservoir_min, "%", minimum=True)
    add(
        "waste_overflow", after["overflow_probability"], budget.waste_overflow_max, "probability", strict=True
    )
    add("cost", after["cost_inr"], budget.cost_max, "INR")
    add("emissions_proxy", after["emissions_proxy_kg"], budget.emissions_proxy_max, "kgCO2e")
    add("route_duration", after["travel_time_minutes"], budget.route_duration_max, "min")
    for name, row in simulated["physical_constraints"].items():
        add(name, row["actual"], row["allowed"], "physical", minimum=row.get("minimum", False))
    return {"passed": all(r["status"] == "PASS" for r in rows), "constraints": rows}


def objective(simulation, ripple, weights: Weights):
    k = simulation["kpis"]
    raw = {
        "cost": k["cost_inr"] / 5000,
        "time": k["response_minutes"] / 60,
        "traffic": max(0, ripple["deltas"]["traffic_delay_seconds"]) / 60,
        "emissions": k["emissions_proxy_kg"] / 30,
    }
    total = sum(weights.model_dump().values())
    contributions = {name: value * getattr(weights, name) / total for name, value in raw.items()}
    return {
        "value": sum(contributions.values()),
        "contributions": contributions,
        "normalization": {
            "cost": "5000 INR",
            "time": "60 min",
            "traffic": "60 sec",
            "emissions": "30 kgCO2e",
        },
    }


def evaluate_action(state, action, request, baseline=None):
    baseline = baseline or simulate_action(
        state,
        Action(id="no-action", label="No action", zone_id=request.zone_id),
        request.horizon_minutes,
        request.seed,
    )
    if action.zone_id != request.zone_id:
        raise ValueError("Action zone must match decision target")
    simulated = simulate_action(state, action, request.horizon_minutes, request.seed)
    ripple = calculate_ripple(baseline, simulated, action)
    return {
        "action": action.model_dump(mode="json"),
        "simulation": simulated,
        "ripple": ripple,
        "budget": check_impact_budget(baseline, simulated, request.budget),
        "objective": objective(simulated, ripple, request.weights),
        "magnitude": [
            action.vehicles,
            abs(action.load_shift_kw) + abs(action.pump_adjustment_m3h) + abs(action.green_delta_seconds),
        ],
    }


def find_minimum_effective_intervention(state, request: DecisionRequest):
    baseline = simulate_action(
        state,
        Action(id="no-action", label="No action", zone_id=request.zone_id),
        request.horizon_minutes,
        request.seed,
    )
    evaluations = [
        evaluate_action(state, a, request, baseline) for a in generate_candidates(state, request.zone_id)
    ]
    feasible = [e for e in evaluations if e["budget"]["passed"]]
    selected = (
        min(feasible, key=lambda e: (*e["magnitude"], e["objective"]["value"], e["action"]["id"]))
        if feasible
        else None
    )
    alternatives = []
    for name, metric in [
        ("Fastest response", "response_minutes"),
        ("Lowest traffic impact", "traffic_delay_seconds"),
        ("Lowest operating cost", "cost_inr"),
    ]:
        if feasible:
            winner = min(feasible, key=lambda e: (e["simulation"]["kpis"][metric], e["action"]["id"]))
            existing = next((p for p in alternatives if p["action_id"] == winner["action"]["id"]), None)
            if existing:
                existing["objectives"].append(name)
            else:
                alternatives.append({"action_id": winner["action"]["id"], "objectives": [name]})
    # Several objectives can pick the same plan. Also expose the next feasible
    # weighted alternatives rather than inventing distinct objective winners.
    for rank, evaluation in enumerate(
        sorted(feasible, key=lambda e: (*e["magnitude"], e["objective"]["value"])), 1
    ):
        if len(alternatives) >= 3:
            break
        if not any(p["action_id"] == evaluation["action"]["id"] for p in alternatives):
            alternatives.append(
                {"action_id": evaluation["action"]["id"], "objectives": [f"Configured-weight rank {rank}"]}
            )
    failures = Counter(
        row["name"] for e in evaluations for row in e["budget"]["constraints"] if row["status"] == "FAIL"
    )
    return {
        "status": "SAFE ACTION FOUND" if selected else "NO SAFE ACTION FOUND",
        "selected": selected,
        "baseline": baseline,
        "evaluations": evaluations,
        "alternatives": alternatives,
        "feasible_count": len(feasible),
        "rejection_summary": dict(failures),
        "request": request.model_dump(mode="json"),
        "options": []
        if selected
        else [
            "Review failed constraints",
            "Add available capacity or an alternate route",
            "Escalate to operator; do not bypass the gate",
        ],
    }
