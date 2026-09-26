import pytest

from backend.app.decision import find_minimum_effective_intervention, generate_candidates
from backend.app.generator import generate_state
from backend.app.schemas import Action, DecisionRequest, ImpactBudget, StressRequest
from backend.app.simulation import simulate_action
from backend.app.stress import run_stress


def stressed():
    return run_stress(generate_state(42), StressRequest())["stressed_state"]


def test_simulation_is_pure_and_repeatable():
    state = generate_state(42)
    saved = state.model_dump_json()
    first = simulate_action(state, Action(id="none", label="No intervention"), 60, 42)
    second = simulate_action(state, Action(id="none", label="No intervention"), 60, 42)
    assert state.model_dump_json() == saved
    assert first["state"] == second["state"]
    assert first["kpis"] == second["kpis"]


def test_minimum_selection_meets_budget_and_uses_fewer_vehicles():
    result = find_minimum_effective_intervention(stressed(), DecisionRequest())
    assert result["status"] == "SAFE ACTION FOUND"
    selected = result["selected"]
    assert selected["action"]["vehicles"] == 1
    assert selected["budget"]["passed"]
    assert selected["simulation"]["kpis"]["overflow_probability"] < 0.1
    assert (
        selected["simulation"]["kpis"]["traffic_delay_seconds"]
        > result["baseline"]["kpis"]["traffic_delay_seconds"]
    )
    assert any(not c["budget"]["passed"] for c in result["evaluations"])
    assert len(result["alternatives"]) >= 2


def test_zero_collateral_budget_returns_no_safe_action():
    request = DecisionRequest(budget=ImpactBudget(traffic_delay_max_delta=0))
    result = find_minimum_effective_intervention(stressed(), request)
    assert result["status"] == "NO SAFE ACTION FOUND"
    assert result["selected"] is None
    assert result["rejection_summary"]


def test_vehicle_failure_and_capacity_never_bypass_gate():
    state = stressed()
    state.available_vehicles = 0
    assert find_minimum_effective_intervention(state, DecisionRequest())["selected"] is None
    state.available_vehicles = 2
    state.vehicle_capacity_m3 = 1
    assert find_minimum_effective_intervention(state, DecisionRequest())["selected"] is None


def test_outage_checks_minimum_over_entire_trajectory():
    state = stressed()
    for z in state.zones:
        z.water.pump_available = False
        z.water.reservoir_m3 = 410
    result = find_minimum_effective_intervention(state, DecisionRequest())
    assert result["selected"] is None
    assert any(
        c["name"] == "reservoir" and c["status"] == "FAIL"
        for c in result["evaluations"][1]["budget"]["constraints"]
    )


def test_invalid_route_and_unknown_zone_fail_explicitly():
    with pytest.raises(ValueError):
        simulate_action(
            generate_state(),
            Action(id="bad", label="bad", kind="waste", vehicles=1, route=["DEPOT", "Z04"]),
            60,
            42,
        )
    with pytest.raises(ValueError):
        generate_candidates(generate_state(), "UNKNOWN")


def test_stress_seed_zone_and_duration_are_respected():
    request = StressRequest(affected_zones=["Z04"], duration_minutes=30)
    first = run_stress(generate_state(), request)
    second = run_stress(generate_state(), request)
    assert first["stressed_state"] == second["stressed_state"]
    assert (
        first["baseline_state"].zones[0].water.demand_m3h == first["stressed_state"].zones[0].water.demand_m3h
    )
    assert (
        first["stressed_state"].zones[-1].water.demand_m3h
        > first["baseline_state"].zones[-1].water.demand_m3h
    )
    assert first["trajectory"][-1]["minute"] == 30
