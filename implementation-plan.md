# UrbanNexus Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for inline execution.

**Goal:** Prove minimum safe intervention across four synthetic urban services.
**Architecture:** Modular monolith, pure numerical simulation, transactional approval.
**Tech Stack:** FastAPI, Pydantic, SQLAlchemy, React/TypeScript/Vite, Leaflet,
ECharts, PostgreSQL (Compose), SQLite (local), MATLAB/Simulink offline validation.
**Spec:** docs/architecture.md and the supplied UrbanNexus brief.

## Global constraints
All operational data is labelled synthetic. No real actuators. Human approval.
Deterministic seed. Hard constraints precede soft objectives. Honest tool status.

## Review focus
Invalid/nonfinite or missing-domain inputs fail validation rather than look safe.
Stale and replayed approvals cannot apply twice; persistence survives app restart.
No safe candidate is a first-class output. Intermediate safety violations count.
Long routes cannot collect after the horizon or exceed physical vehicle capacity.
Unverified external artifacts cannot be presented as MATLAB/SUMO validation.

### Task 1: Foundation and state
Files: pyproject.toml, backend/app/schemas.py, generator.py, db.py; tests/test_state.py.
Interfaces: generate_state(seed:int)->UrbanState; SQLAlchemy state/passport/audit tables.
- [x] Write/run failing tests for repeatability, invalid bounds, unique zones and persistence.
- [x] Implement typed state, deterministic generator and database schema.
- [x] Run pytest and commit a working foundation.

### Task 2: Domain models and external prototypes
Files: domains.py, integrations.py, matlab/, simulink/, sumo/, tests/test_domains.py.
Interfaces: forecast(values)->forecast; water_step(...); traffic_step(...); overflow_risk(...).
- [x] Write/run failing conservation, uncertainty, forecasting and schedule feasibility tests.
- [x] Implement numerical models, capability reporting and executable external integrations.
- [x] Run unit tests; run MATLAB/SUMO if installed; record unavailable runtimes honestly.

### Task 3: Coupled simulation and minimum search
Files: simulation.py, decision.py, stress.py; tests/test_decision.py.
Interfaces: simulate_action(state,action,horizon_minutes,seed)->SimulationResult;
check_impact_budget(...)->BudgetResult; find_minimum_effective_intervention(...).
- [x] Write/run failing purity, cross-domain coupling, minimum selection, unsafe trajectory,
  no-feasible, vehicle failure, duration and scenario reproducibility tests.
- [x] Implement route enumeration, time-aligned counterfactuals, ripple and stress trajectories.
- [x] Run all tests and commit the complete numerical decision path.

### Task 4: API and auditable approval
Files: service.py, main.py; tests/test_api.py.
Interfaces: all /api/v1 endpoints in supplied brief; atomic approval and state revision.
- [x] Write/run failing end-to-end, reject, stale/replay, malformed and restart tests.
- [x] Implement API, persisted passports/audit, budget recheck and simulated outcome.
- [x] Verify OpenAPI and database transactions; commit.

### Task 5: Operator command center
Files: frontend/src/*, package.json, Dockerfile, docker-compose.yml.
Interfaces: typed API client; real current state, scenario, budget and passport views.
- [x] Build the React command center with local Leaflet map and computed ECharts trajectories.
- [x] Add controls for stress, budgets/weights, arena selection, approve/reject and export.
- [x] Typecheck/build and exercise actual browser stress-to-approval and no-safe-action flows.

### Task 6: Reproduction and evidence
Files: scripts/demo.py, benchmark.py, evaluate.py, validate_matlab.py, README.md, docs/*, CI.
- [x] Run deterministic demo, held-out validation, benchmarks, backend suite and frontend build.
- [x] Review safety contracts, fix material findings with regression tests.
- [x] Record measured evidence, exact external-runtime limitations and startup commands.
- [x] Commit verified working state and deliver concise instructions.

## Remaining external validation

- [ ] Run licensed MATLAB and Simulink, generate real .slx models and pass the numerical parity check. Runtime unavailable here; authored code is not execution evidence.
