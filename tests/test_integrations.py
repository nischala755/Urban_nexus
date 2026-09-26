import json

import pytest

from backend.app.integrations import reference_fixture, validate_matlab_output


def test_matlab_output_requires_actual_producer_and_matching_input():
    fixture, reference = reference_fixture()
    with pytest.raises(ValueError, match="producer"):
        validate_matlab_output({**reference, "producer": "Python"}, fixture)
    with pytest.raises(ValueError, match="fingerprint"):
        validate_matlab_output(
            {**reference, "producer": "MATLAB+Simulink", "input_fingerprint": "bad"}, fixture
        )


def test_matlab_parity_rejects_wrong_dynamics_and_nonfinite_values():
    fixture, reference = reference_fixture()
    # This is a contract test fixture, never a claimed MATLAB execution.
    output = json.loads(json.dumps(reference))
    output.update(producer="MATLAB+Simulink", runtime_version="contract-test")
    assert validate_matlab_output(output, fixture)["passed"]
    output["water_volume_m3"][15] += 1
    with pytest.raises(ValueError, match="water_volume"):
        validate_matlab_output(output, fixture)
    output["water_volume_m3"][15] = float("nan")
    with pytest.raises(ValueError):
        validate_matlab_output(output, fixture)
