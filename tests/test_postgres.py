"""Run against a dedicated disposable database when TEST_POSTGRES_URL is supplied."""

import os

import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="PostgreSQL test service not configured")
def test_postgresql_persists_and_gates_approval():
    with TestClient(create_app(os.environ["TEST_POSTGRES_URL"])) as client:
        client.post("/api/v1/stress-tests/run", json={}).raise_for_status()
        result = client.post("/api/v1/interventions/minimum-effective", json={}).json()
        action_id = result["passport"]["id"]
        url = f"/api/v1/action-passports/{action_id}/approve"
        assert client.post(url, json={"operator": "PostgreSQL integration test"}).status_code == 200
        assert client.post(url, json={"operator": "Replay"}).status_code == 409
