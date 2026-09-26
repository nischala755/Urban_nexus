"""Runtime capability status, never a claim that an executable has been validated."""

import hashlib
import json
import math
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def find_matlab():
    configured = os.getenv("MATLAB_EXECUTABLE")
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("matlab")


def capabilities():
    from .sumo_adapter import find_sumo

    path = ROOT / "artifacts" / "matlab-output.json"
    matlab_status = "unavailable — Python reference; parity not yet validated"
    if find_matlab():
        matlab_status = "available — run scripts/validate_matlab.py to validate"
    if path.exists():
        try:
            report = validate_matlab_output(json.loads(path.read_text()), reference_fixture()[0])
            if report["passed"]:
                matlab_status = "offline MATLAB/Simulink parity validated; Python reference active"
        except (ValueError, OSError):
            matlab_status = "invalid validation artifact — Python reference active"
    return {
        "matlab_simulink": matlab_status,
        "traffic": "deterministic fluid-queue reference active",
        "sumo": "SUMO/TraCI installed; separate microscopic validation available"
        if find_sumo()
        else "unavailable — fluid-queue fallback",
        "degraded": "validated" not in matlab_status or "not yet" in matlab_status,
        "operational_optimizer": "deterministic exhaustive enumeration; no LLM",
        "municipal_connection": False,
    }


def reference_fixture():
    from .domains import energy_schedule, forecast, traffic_step, water_step

    inputs = {
        "schema_version": 1,
        "steps": 60,
        "initial_volume_m3": 600,
        "initial_queue": 10,
        "water_demand_before": 140,
        "water_demand_after": 210,
        "step_minute": 10,
        "energy_base_kw": [100, 300, 120],
        "tariffs": [3, 9, 4],
        "flexible_kwh": 60,
        "capacity_kw": 200,
        "history": list(range(1, 13)),
        "magnitudes": [0, 1, 1, 2],
        "objectives": [0, 0.5, 0.3, 0.1],
        "feasible": [False, True, True, True],
    }
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
    inputs["input_fingerprint"] = fingerprint
    volume, queue = 600.0, 10.0
    volumes, powers, queues = [], [], []
    for minute in range(61):
        volumes.append(volume)
        queues.append(queue)
        water = water_step(volume, 140 if minute < 10 else 210, 1000, 300, True)
        powers.append(water["pump_kw"])
        volume = water["volume_m3"]
        queue = traffic_step(queue, 20 if minute < 10 else 40, 30)["queue_vehicles"]
    reference = {
        "schema_version": 1,
        "input_fingerprint": fingerprint,
        "model_version": "offline-parity/1.0",
        "water_volume_m3": volumes,
        "pump_kw": powers,
        "traffic_queue": queues,
        "forecast": forecast(inputs["history"])["predicted"],
        "schedule_slot_zero_based": energy_schedule(inputs["energy_base_kw"], inputs["tariffs"], 60, 200)[
            "slot"
        ],
        "selected_index_zero_based": 2,
    }
    return inputs, reference


def validate_matlab_output(output, fixture, tolerance=1e-6):
    if output.get("producer") != "MATLAB+Simulink":
        raise ValueError("Invalid producer; MATLAB+Simulink execution required")
    if output.get("input_fingerprint") != fixture["input_fingerprint"]:
        raise ValueError("MATLAB input fingerprint does not match current fixture")
    if output.get("schema_version") != 1 or output.get("model_version") != "offline-parity/1.0":
        raise ValueError("Unknown external model schema/version")
    _, reference = reference_fixture()
    errors = {}
    for key in [
        "water_volume_m3",
        "pump_kw",
        "traffic_queue",
        "forecast",
        "schedule_slot_zero_based",
        "selected_index_zero_based",
    ]:
        expected = reference[key] if isinstance(reference[key], list) else [reference[key]]
        actual = output.get(key)
        actual = actual if isinstance(actual, list) else [actual]
        if len(actual) != len(expected) or not all(
            isinstance(x, (int, float)) and math.isfinite(x) for x in actual
        ):
            raise ValueError(f"Invalid MATLAB {key} output")
        errors[key] = max(abs(a - e) for a, e in zip(actual, expected))
        if errors[key] > tolerance:
            raise ValueError(f"MATLAB parity failed for {key}: {errors[key]} > {tolerance}")
    return {
        "passed": True,
        "producer": "MATLAB+Simulink",
        "tolerance": tolerance,
        "max_absolute_errors": errors,
        "runtime_version": output.get("runtime_version"),
        "input_fingerprint": fixture["input_fingerprint"],
    }
