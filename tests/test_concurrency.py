import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_simultaneous_approvals_apply_at_most_one_action(tmp_path, monkeypatch):
    from backend.app import service

    evaluate = service.evaluate_action
    rendezvous = Barrier(2)

    def evaluate_together(*args, **kwargs):
        result = evaluate(*args, **kwargs)
        rendezvous.wait(timeout=10)
        return result

    monkeypatch.setattr(service, "evaluate_action", evaluate_together)
    database_url = os.getenv("TEST_POSTGRES_URL", f"sqlite:///{tmp_path / 'concurrent.db'}")
    with TestClient(create_app(database_url)) as client:
        client.post("/api/v1/stress-tests/run", json={}).raise_for_status()
        passports = [
            client.post("/api/v1/interventions/minimum-effective", json={}).json()["passport"]
            for _ in range(2)
        ]
        initial_version = client.get("/api/v1/state/current").json()["version"]

        def approve(passport):
            return client.post(
                f"/api/v1/action-passports/{passport['id']}/approve", json={"operator": "Concurrent test"}
            ).status_code

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(approve, passports))
        assert sorted(statuses) == [200, 409]
        assert client.get("/api/v1/state/current").json()["version"] == initial_version + 1
