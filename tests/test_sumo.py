import pytest

from backend.app.sumo_adapter import find_sumo, run_validation


@pytest.mark.skipif(not find_sumo(), reason="Optional SUMO runtime not installed")
def test_real_sumo_runs_both_worlds_and_records_traffic_effect(tmp_path):
    report = run_validation(tmp_path)
    assert report["status"] == "executed"
    assert report["baseline"]["trips"] > 0
    assert report["action"]["trips"] == report["baseline"]["trips"] + 1
    assert report["action"]["unfinished_trips"] == 0
    assert report["baseline"]["unfinished_trips"] == 0
    assert report["baseline"]["mean_background_travel_seconds"] > 0
    assert report["background_delay_delta_seconds"] != 0
