"""Held-out synthetic evaluation; no external data or model accuracy is invented."""

import json
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.domains import anomaly_score, forecast


def main():
    rng = random.Random(20260926)
    metrics = {}
    for domain, base in [("energy_kw", 400), ("water_m3h", 140), ("traffic_vpm", 20)]:
        zones = []
        for zone in range(1, 5):
            errors, persistence = [], []
            tp = fp = fn = 0
            for case in range(100):
                slope = rng.uniform(-0.005, 0.005) * base
                values = [base + slope * t + rng.gauss(0, base * 0.015) for t in range(14)]
                predicted = forecast(values[:12])["predicted"]
                errors.append(abs(predicted - values[12]))
                persistence.append(abs(values[11] - values[12]))
                anomalous = case % 5 == 0
                observation = values[12] + (base * 0.5 if anomalous else 0)
                detected = anomaly_score(values[:12], observation) > 3
                tp += detected and anomalous
                fp += detected and not anomalous
                fn += not detected and anomalous
            zones.append(
                {
                    "zone_id": f"Z{zone:02}",
                    "held_out_cases": 100,
                    "persistence_mae": statistics.mean(persistence),
                    "selected_model_mae": statistics.mean(errors),
                    "rmse": statistics.mean(e * e for e in errors) ** 0.5,
                    "anomaly_precision": tp / max(1, tp + fp),
                    "anomaly_recall": tp / max(1, tp + fn),
                    "anomaly_f1": 2 * tp / max(1, 2 * tp + fp + fn),
                }
            )
        metrics[domain] = zones
    report = {
        "source_type": "synthetic",
        "seed": 20260926,
        "generator": "linear drift + Gaussian measurement noise; labelled 50% surges",
        "protocol": "12 history points, next unseen point; 100 cases per zone/domain; no test-label fitting",
        "limitations": "Illustrative synthetic validation only. Does not establish field calibration or disaster prediction.",
        "metrics": metrics,
    }
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    (output / "evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
