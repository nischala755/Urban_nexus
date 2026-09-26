"""Measured local wall-clock timings, not promised production performance."""

import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient

from backend.app.main import create_app


def main():
    results = {}
    with TestClient(create_app("sqlite:///:memory:")) as client:
        client.post("/api/v1/stress-tests/run", json={}).raise_for_status()
        for name, path, method, target in [
            ("current_state", "/api/v1/state/current", "get", 500),
            ("candidate_generation", "/api/v1/interventions/candidates", "post", 2000),
            ("minimum_intervention", "/api/v1/interventions/minimum-effective", "post", 5000),
            ("stress_test", "/api/v1/stress-tests/run", "post", 10000),
        ]:
            samples = []
            for _ in range(10):
                start = time.perf_counter()
                response = client.get(path) if method == "get" else client.post(path, json={})
                response.raise_for_status()
                samples.append((time.perf_counter() - start) * 1000)
            results[name] = {
                "samples": 10,
                "median_ms": statistics.median(samples),
                "max_ms": max(samples),
                "target_ms": target,
                "target_met": max(samples) < target,
            }
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "database": "SQLite in-memory",
        "transport": "in-process FastAPI TestClient; includes serialization, excludes network",
        "results": results,
    }
    output = Path("artifacts")
    output.mkdir(exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
