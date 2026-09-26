import pytest

from backend.app.domains import (
    anomaly_score,
    energy_schedule,
    forecast,
    overflow_risk,
    traffic_step,
    water_step,
)


def test_water_mass_balance_and_pump_power():
    # 600 + (200 - 140) / 60 = 601 m3; 200 * .6 = 120 kW.
    result = water_step(600, 140, 1000, 300, True, adjustment=35)
    assert result["volume_m3"] == pytest.approx(601)
    assert result["pump_kw"] == pytest.approx(120)
    assert water_step(600, 120, 1000, 300, False)["volume_m3"] == 598


def test_queue_conservation_and_green_response():
    assert traffic_step(10, 40, 30)["queue_vehicles"] == 20
    assert traffic_step(10, 40, 40)["queue_vehicles"] == 10
    assert traffic_step(0, 10, 30)["queue_vehicles"] == 0


def test_overflow_accounts_for_before_and_after_collection():
    assert overflow_risk(80, 20, 4, 60) == pytest.approx(0.5)
    assert overflow_risk(80, 20, 4, 60, collection_minute=10) < 0.01
    assert overflow_risk(99, 20, 4, 60, collection_minute=30) > 0.99
    assert overflow_risk(80, 20, 4, 180, collection_minute=10) > 0
    assert overflow_risk(100, 0, 0, 60, collection_minute=0) == 1


def test_forecast_handles_flat_and_rising_history_without_fake_confidence():
    assert forecast([10] * 12)["predicted"] == 10
    result = forecast(list(range(1, 13)))
    assert result["predicted"] == pytest.approx(13)
    assert result["method"] == "linear_trend"
    assert result["validation_mae"] == 0
    assert result["interval_kind"] == "held-out absolute residual envelope; not calibrated"


def test_robust_anomaly_distinguishes_normal_and_surge():
    history = [98, 101, 102, 99, 100, 98, 102, 101]
    assert anomaly_score(history, 100) < 3
    assert anomaly_score(history, 160) > 3


def test_energy_scheduling_preserves_service_and_honours_capacity():
    schedule = energy_schedule([100, 300, 120], [3, 9, 4], 60, 200)
    assert schedule["feasible"]
    assert schedule["slot"] == 0
    assert sum(schedule["load_kw"]) == 60
    assert not energy_schedule([300, 300], [3, 4], 60, 200)["feasible"]
