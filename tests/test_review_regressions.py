import os
import subprocess
import sys

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.db import StateRow, Store
from backend.app.decision import evaluate_action, generate_candidates
from backend.app.domains import predictions
from backend.app.generator import generate_state
from backend.app.schemas import Action, DecisionRequest, ImpactBudget, StressRequest, UrbanState
from backend.app.service import Service
from backend.app.simulation import simulate_action
from backend.app.stress import run_stress


def test_ingest_cannot_overwrite_a_historical_snapshot(tmp_path):
    store = Store(f"sqlite:///{tmp_path / 'history.db'}")
    initial = generate_state()
    store.initialize(initial)
    changed = initial.model_copy(deep=True)
    changed.zones[-1].waste.fill_pct = 99
    stored, _ = Service(store).replace_state(changed, "synthetic_ingest", {})
    assert stored.id != initial.id
    with Session(store.engine) as session:
        assert session.get(StateRow, initial.id).payload == initial.model_dump(mode="json")


def test_peak_collateral_violation_is_not_hidden_by_average():
    state = run_stress(generate_state(), StressRequest())["stressed_state"]
    action = next(a for a in generate_candidates(state) if a.id == "collect-1-1")
    result = evaluate_action(
        state, action, DecisionRequest(budget=ImpactBudget(traffic_delay_max_delta=0.45))
    )
    row = next(c for c in result["budget"]["constraints"] if c["name"] == "traffic_delay")
    assert row["actual"] > 0.5
    assert row["status"] == "FAIL"


def test_route_must_finish_before_available_vehicle_can_be_reused():
    action = generate_candidates(generate_state())[1]
    request = DecisionRequest(
        horizon_minutes=15, budget=ImpactBudget(traffic_delay_max_delta=100, energy_demand_max_delta=100)
    )
    result = evaluate_action(generate_state(), action, request)
    assert result["simulation"]["kpis"]["response_minutes"] < 15
    assert result["simulation"]["kpis"]["travel_time_minutes"] > 15
    assert not result["budget"]["passed"]


def test_deferred_energy_is_repaid_without_erasing_flexible_load():
    state = generate_state()
    idle = Action(id="none", label="No action")
    shift = Action(id="shift", label="Defer 20 kW", kind="energy", load_shift_kw=20)
    baseline = simulate_action(state, idle, 60, 42)
    shifted = simulate_action(state, shift, 60, 42)
    next_state = UrbanState.model_validate(shifted["state"])
    assert next_state.zones[-1].energy.flexible_kw == 60
    assert next_state.zones[-1].energy.deferred_kwh == pytest.approx(20)
    recovery_a = simulate_action(next_state, idle, 60, 42)
    assert recovery_a["state"]["zones"][-1]["energy"]["deferred_kwh"] == pytest.approx(10)
    recovery_b = simulate_action(UrbanState.model_validate(recovery_a["state"]), idle, 60, 42)
    assert recovery_b["state"]["zones"][-1]["energy"]["deferred_kwh"] == pytest.approx(0, abs=1e-9)
    reference = simulate_action(UrbanState.model_validate(baseline["state"]), idle, 120, 42)
    assert shifted["kpis"]["energy_kwh"] + recovery_a["kpis"]["energy_kwh"] + recovery_b["kpis"][
        "energy_kwh"
    ] == pytest.approx(baseline["kpis"]["energy_kwh"] + reference["kpis"]["energy_kwh"])


def test_fixed_step_forecasts_expose_their_actual_horizon():
    for horizon in [15, 60, 180]:
        result = predictions(generate_state(), horizon)[0]
        assert result["forecast_horizon_minutes"] == 5
        assert result["waste_horizon_minutes"] == horizon


def test_unsupported_signal_cycle_is_rejected():
    data = generate_state().model_dump()
    data["zones"][0]["traffic"]["cycle_seconds"] = 120
    with pytest.raises(ValidationError):
        UrbanState.model_validate(data)


def test_demo_cli_works_on_windows_legacy_console(tmp_path):
    result = subprocess.run(
        [sys.executable, "scripts/demo.py", "--skip-sumo", "--output", str(tmp_path)],
        env={**os.environ, "PYTHONIOENCODING": "cp1252"},
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "NO SAFE ACTION FOUND" in result.stdout
