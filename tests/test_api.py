import pytest
from fastapi.testclient import TestClient

from backend.app.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(f"sqlite:///{tmp_path / 'api.db'}")) as c:
        yield c


def recommend(client):
    assert client.post("/api/v1/stress-tests/run", json={}).status_code == 200
    response = client.post("/api/v1/interventions/minimum-effective", json={})
    assert response.status_code == 200
    return response.json()


def test_approval_records_audit_updates_state_and_prevents_replay(client):
    passport = recommend(client)["passport"]
    before = client.get("/api/v1/state/current").json()
    assert passport["approval_status"] == "pending"
    url = f"/api/v1/action-passports/{passport['id']}/approve"
    response = client.post(url, json={"operator": "Test operator"})
    assert response.status_code == 200
    after = client.get("/api/v1/state/current").json()
    assert after["version"] == before["version"] + 1
    assert (
        after["state"]["zones"][-1]["waste"]["fill_pct"] < before["state"]["zones"][-1]["waste"]["fill_pct"]
    )
    assert response.json()["approval_status"] == "approved"
    assert client.post(url, json={"operator": "Test"}).status_code == 409
    assert client.get("/api/v1/state/current").json() == after
    assert any(row["event"] == "approved_and_simulated" for row in client.get("/api/v1/audit").json())
    comparison = client.get("/api/v1/kpis/comparison").json()
    assert comparison["action_id"] == passport["id"]
    assert comparison["after"]["overflow_probability"] < comparison["before"]["overflow_probability"]


def test_rejection_does_not_change_ward(client):
    passport = recommend(client)["passport"]
    before = client.get("/api/v1/state/current").json()
    url = f"/api/v1/action-passports/{passport['id']}"
    assert client.post(url + "/reject", json={"operator": "Test", "note": "Review route"}).status_code == 200
    assert client.get("/api/v1/state/current").json() == before
    assert client.post(url + "/approve", json={"operator": "Test"}).status_code == 409


def test_stale_passport_cannot_act_after_new_scenario(client):
    passport = recommend(client)["passport"]
    client.post("/api/v1/stress-tests/run", json={"scenario": "vehicle_failure"})
    response = client.post(f"/api/v1/action-passports/{passport['id']}/approve", json={"operator": "Test"})
    assert response.status_code == 409
    assert "stale" in response.json()["detail"].lower()


def test_infeasible_request_creates_no_passport(client):
    client.post("/api/v1/stress-tests/run", json={})
    result = client.post(
        "/api/v1/interventions/minimum-effective", json={"budget": {"traffic_delay_max_delta": 0}}
    ).json()
    assert result["status"] == "NO SAFE ACTION FOUND"
    assert result["passport"] is None
    assert client.get("/api/v1/action-passports").json() == []


def test_invalid_inputs_and_unknown_resources_are_explicit(client):
    assert client.post("/api/v1/stress-tests/run", json={"severity": -1}).status_code == 422
    assert client.post("/api/v1/stress-tests/run", json={"affected_zones": ["bad"]}).status_code == 422
    assert (
        client.post(
            "/api/v1/interventions/minimum-effective",
            json={"weights": {"cost": 0, "time": 0, "traffic": 0, "emissions": 0}},
        ).status_code
        == 422
    )
    assert client.get("/api/v1/action-passports/not-found").status_code == 404
    assert client.post("/api/v1/interventions/minimum-effective", json={"zone_id": "bad"}).status_code == 422


def test_health_and_openapi_and_all_domains_are_exposed(client):
    assert client.get("/health").json()["data_source"] == "synthetic"
    assert "/api/v1/action-passports/{passport_id}/approve" in client.get("/openapi.json").json()["paths"]
    assert len(client.get("/api/v1/predictions").json()) == 4
    result = client.post("/api/v1/interventions/candidates", json={}).json()
    assert {a["kind"] for a in result["domain_actions"]} == {"traffic", "energy", "water"}


def test_passport_and_comparison_survive_restart(tmp_path):
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    with TestClient(create_app(url)) as first:
        passport = recommend(first)["passport"]
        first.post(f"/api/v1/action-passports/{passport['id']}/approve", json={"operator": "Test"})
        state = first.get("/api/v1/state/current").json()
    with TestClient(create_app(url)) as second:
        assert second.get("/api/v1/state/current").json() == state
        assert (
            second.get(f"/api/v1/action-passports/{passport['id']}").json()["approval_status"] == "approved"
        )
        assert second.get("/api/v1/kpis/comparison").json()["action_id"] == passport["id"]
