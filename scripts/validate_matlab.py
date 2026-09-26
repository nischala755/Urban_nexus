"""Run licensed MATLAB/Simulink and validate real outputs; never fabricate parity."""

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.integrations import ROOT, find_matlab, reference_fixture, validate_matlab_output


def main():
    output_dir = ROOT / "artifacts"
    output_dir.mkdir(exist_ok=True)
    fixture, _ = reference_fixture()
    input_path = output_dir / "matlab-input.json"
    output_path = output_dir / "matlab-output.json"
    input_path.write_text(json.dumps(fixture, indent=2))
    executable = find_matlab()
    if not executable:
        report = {
            "passed": False,
            "status": "unavailable",
            "producer": None,
            "reason": "MATLAB executable not found. Install licensed MATLAB + Simulink and set MATLAB_EXECUTABLE.",
            "fallback": "Python numerical reference; cross-runtime parity NOT validated",
        }
        (output_dir / "matlab-validation.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report, indent=2))
        return 2

    def quote(path):
        return str(path).replace("'", "''").replace("\\", "/")

    command = f"addpath('{quote(ROOT / 'matlab')}'); run_validation('{quote(input_path)}','{quote(output_path)}','{quote(output_dir / 'simulink')}')"
    run = subprocess.run(
        [executable, "-batch", command], cwd=ROOT, capture_output=True, text=True, timeout=600, check=False
    )
    (output_dir / "matlab.log").write_text(run.stdout + run.stderr)
    if run.returncode:
        print("MATLAB failed; see artifacts/matlab.log. No parity claim made.")
        return run.returncode
    report = validate_matlab_output(json.loads(output_path.read_text()), fixture)
    (output_dir / "matlab-validation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
