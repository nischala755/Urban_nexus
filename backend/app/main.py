"""UrbanNexus versioned HTTP API; no hardware-control endpoints exist."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .db import Store
from .decision import domain_candidates, evaluate_action, generate_candidates
from .domains import MODEL_VERSIONS, predictions
from .generator import generate_state
from .integrations import capabilities
from .network import EDGES
from .schemas import (
    Action,
    Approval,
    DecisionRequest,
    EvaluateRequest,
    ResetRequest,
    StressRequest,
    UrbanState,
)
from .service import ConflictError, MissingError, Service
from .simulation import instant_kpis, simulate_action
from .stress import run_stress


def create_app(database_url=None):
    @asynccontextmanager
    async def lifespan(app):
        store = Store(database_url or os.getenv("DATABASE_URL", "sqlite:///urbannexus.db"))
        store.initialize(generate_state(42))
        app.state.store, app.state.service = store, Service(store)
        yield
        store.engine.dispose()

    app = FastAPI(
        title="UrbanNexus",
        version="0.1.0",
        lifespan=lifespan,
        description="Synthetic ward decision support. No real municipal control. Trusted-local prototype.",
    )

    @app.exception_handler(ValueError)
    async def invalid_input(_, exc):
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(ConflictError)
    async def conflict(_, exc):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(MissingError)
    async def missing(_, exc):
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/health")
    def health():
        app.state.store.current()
        return {
            "status": "ok",
            "data_source": "synthetic",
            "mode": "Prototype / Simulated Sensor Feed",
            "capabilities": capabilities(),
            "model_versions": MODEL_VERSIONS,
        }

    @app.get("/api/v1/state/current")
    def current():
        state, version = app.state.store.current()
        return {"state": state, "version": version, "kpis": instant_kpis(state, state.zones[-1].id)}

    @app.post("/api/v1/state/ingest")
    def ingest(state: UrbanState):
        updated, version = app.state.service.replace_state(
            state, "synthetic_ingest", {"provenance": state.metadata.model_dump()}
        )
        return {"state": updated, "version": version}

    @app.post("/api/v1/state/reset")
    def reset(request: ResetRequest):
        state, version = app.state.service.replace_state(
            generate_state(request.seed), "scenario_reset", {"seed": request.seed}
        )
        return {"state": state, "version": version}

    @app.get("/api/v1/zones")
    def zones():
        return {
            "zones": app.state.store.current()[0].zones,
            "roads": EDGES,
            "depot": {"id": "DEPOT", "x": 8, "y": 45},
            "coordinates": "synthetic schematic; not geographic",
        }

    @app.get("/api/v1/predictions")
    def predict():
        return predictions(app.state.store.current()[0])

    @app.get("/api/v1/alerts")
    def alerts():
        return [{"zone_id": p["zone_id"], **a} for p in predict() for a in p["alerts"]]

    @app.post("/api/v1/interventions/candidates")
    def candidates(request: DecisionRequest):
        state = app.state.store.current()[0]
        return {
            "actions": generate_candidates(state, request.zone_id),
            "domain_actions": domain_candidates(state, request.zone_id),
        }

    @app.post("/api/v1/interventions/evaluate")
    @app.post("/api/v1/what-if/simulate")
    def evaluate(request: EvaluateRequest):
        return evaluate_action(app.state.store.current()[0], request.action, request)

    @app.post("/api/v1/interventions/minimum-effective")
    def minimum(request: DecisionRequest):
        return app.state.service.recommend(request)

    @app.post("/api/v1/ripple/evaluate")
    def ripple(request: EvaluateRequest):
        return evaluate(request)["ripple"]

    @app.post("/api/v1/impact-budget/check")
    def budget(request: EvaluateRequest):
        return evaluate(request)["budget"]

    @app.post("/api/v1/stress-tests/run")
    def stress(request: StressRequest):
        # Each stress test is an independent reproducible experiment, not cumulative.
        result = run_stress(generate_state(request.seed), request)
        app.state.service.replace_state(result["stressed_state"], "stress_test", request.model_dump())
        result["candidate_actions"] = generate_candidates(
            result["stressed_state"], request.affected_zones[-1]
        )
        return jsonable_encoder(result)

    @app.get("/api/v1/action-passports")
    def passports():
        return app.state.service.passports()

    @app.get("/api/v1/action-passports/{passport_id}")
    def passport(passport_id: str):
        return app.state.service.passport(passport_id)

    @app.post("/api/v1/action-passports/{passport_id}/approve")
    def approve(passport_id: str, decision: Approval):
        return app.state.service.decide(passport_id, decision, True)

    @app.post("/api/v1/action-passports/{passport_id}/reject")
    def reject(passport_id: str, decision: Approval):
        return app.state.service.decide(passport_id, decision, False)

    @app.get("/api/v1/kpis/baseline")
    def baseline():
        state = app.state.store.current()[0]
        return simulate_action(
            state, Action(id="none", label="No action", zone_id=state.zones[-1].id), 60, state.metadata.seed
        )["kpis"]

    @app.get("/api/v1/kpis/comparison")
    def comparison():
        return app.state.service.comparison()

    @app.get("/api/v1/audit")
    def audit():
        return app.state.service.audit()

    frontend = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if frontend.exists():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="command-center")
    return app


app = create_app()
