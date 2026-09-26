"""One-command deterministic end-to-end acceptance demo, in an isolated database."""

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient

from backend.app.main import create_app


def run_demo():
    with (
        TemporaryDirectory() as directory,
        TestClient(create_app(f"sqlite:///{Path(directory) / 'demo.db'}")) as client,
    ):

        def post(path, body):
            response = client.post("/api/v1/" + path, json=body)
            response.raise_for_status()
            return response.json()

        normal = client.get("/api/v1/state/current").json()
        stress = post("stress-tests/run", {"seed": 42})
        result = post("interventions/minimum-effective", {"seed": 42})
        assert result["selected"] and result["selected"]["budget"]["passed"]
        passport = result["passport"]
        approved = post(
            f"action-passports/{passport['id']}/approve",
            {
                "operator": "AUTOMATED ACCEPTANCE TEST — simulated human approval",
                "note": "Test harness only. Interactive UI requires a person to approve.",
            },
        )
        comparison = client.get("/api/v1/kpis/comparison").json()
        post("stress-tests/run", {"seed": 42})
        unsafe = post("interventions/minimum-effective", {"budget": {"traffic_delay_max_delta": 0}})
        assert unsafe["selected"] is None and unsafe["passport"] is None
        return {
            "scenario": "Peak-Hour Urban Stress",
            "source_type": "synthetic",
            "seed": 42,
            "normal_state": normal,
            "stress": stress,
            "passport": approved,
            "comparison": comparison,
            "candidate_summary": [
                {"action": e["action"], "kpis": e["simulation"]["kpis"], "budget": e["budget"]}
                for e in result["evaluations"]
            ],
            "safe_failure": unsafe["status"],
            "health": client.get("/health").json(),
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-sumo", action="store_true", help="Run only the core numerical/API acceptance path"
    )
    parser.add_argument("--output", type=Path, help="Evidence directory (default: artifacts)")
    args = parser.parse_args()
    output = args.output or Path(__file__).resolve().parents[1] / "artifacts"
    output.mkdir(exist_ok=True)
    report = run_demo()
    if not args.skip_sumo:
        from backend.app.sumo_adapter import run_validation

        report["sumo_validation"] = run_validation(output / "sumo")
    (output / "demo.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    p = report["passport"]
    label = p["proposed_intervention"]["label"].replace("→", "->")
    print(f"SYNTHETIC DEMO / seed 42: {label}")
    print(
        f"Overflow probability: {p['baseline_kpi']['overflow_probability']:.4%} -> {p['predicted_kpi']['overflow_probability']:.4%}"
    )
    print(
        f"All hard constraints passed; simulated operator approval recorded. {report['safe_failure']} with zero traffic allowance."
    )
    print("Evidence: artifacts/demo.json")
