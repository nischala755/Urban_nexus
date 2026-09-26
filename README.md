# UrbanNexus

A working, synthetic ward-level decision-support prototype: **find the smallest
intervention that meets a service target without exceeding cross-service limits**.

The core demonstration covers four connected services, waste-route enumeration,
counterfactual Urban Ripple, configurable Impact Budget, Safe-to-Act Gate, an
auditable Action Passport, human approval and an updated simulated ward state.
There is no real municipal connection. Every operational reading is synthetic.

## Deploy on Render

[Deploy to Render](https://render.com/deploy?repo=https://github.com/nischala755/Urban_nexus)
creates the Docker web service and PostgreSQL database from `render.yaml`.
Both default to Free. **The free database expires after 30 days.**
See [deployment steps and limitations](docs/render-deployment.md).

## Run locally

Requires Python 3.11+ and Node.js 22+ (tested with Python 3.12 / Node 24).
From the repository root, Windows PowerShell:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.lock -e .
.venv/Scripts/python scripts/start.py --build
```

macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock -e .
.venv/bin/python scripts/start.py --build
```

Open **http://127.0.0.1:8000**. API documentation: **http://127.0.0.1:8000/docs**.
The server creates the SQLite schema and seeded ward automatically. Stop with
Ctrl+C. Data persists in `urbannexus.db`; Reset creates a new audited scenario.
Set `DATABASE_URL` in the process environment to use another database. `.env` is
a Compose convention; the plain Python server does not automatically load it.

For development, run `python -m uvicorn backend.app.main:app --reload` and
`npm --prefix frontend run dev` in separate terminals after activating the venv.
The Vite dev server proxies the backend on port 8000.

## One-command deterministic demo

After installation, using the virtual environment's Python:

```bash
python scripts/demo.py
```

This runs an isolated API acceptance demonstration with seed 42: normal state →
peak-hour disturbance at minute 10 → prediction → candidates → simulation →
budget gate → minimum intervention → passport → explicitly labelled test-harness
approval → outcome. It also demonstrates no safe action under a zero traffic
allowance. It does not modify the interactive operator database.

Evidence is written to `artifacts/demo.json`. If SUMO is installed, the command
also runs the real microscopic traffic comparison. Use `--skip-sumo` for the
fast core demo. The interactive application always requires a person to click
**Approve & simulate**; a script's acceptance-test approval is not a real operator.

## Try the command center

1. Run **Peak-Hour Urban Stress**, seed 42, severity 1, 60 minutes, all zones.
2. Inspect the four services and the forecast for Z04.
3. Select **Find minimum intervention**. Compare feasible plans and rejected routes.
4. Inspect Urban Ripple and the per-constraint gate, then review the Action Passport.
5. Approve to simulate implementation, or reject to leave the ward unchanged.
6. Run the stress test again, set **Traffic delay increase** to 0 and evaluate.
   The result is **NO SAFE ACTION FOUND**, with no passport or approval button.

Changing budgets requires a fresh evaluation. Scenario resets, ingests and approval
advance the ward revision; pending passports based on older revisions cannot act.
The map is a local schematic using Leaflet's simple coordinates, not a Bengaluru map.

## Docker + PostgreSQL

```bash
docker compose up --build
```

The same UI/API runs at port 8000, bound to loopback. PostgreSQL 16 has a persistent
named volume and a readiness check. The app runs as a non-root container user.
The image was built and both services passed health checks locally. The PostgreSQL
approval/replay integration test also passed inside the running container. CI
includes the same database test; no remote CI run is claimed until it executes.

## MATLAB, Simulink and SUMO — actual status

**MATLAB/Simulink are authored but not executed in this environment.** No licensed
installation was found. This means the brief's mandatory actual MATLAB result and
Simulink `.slx` demonstration are **still outstanding**. No Python result is labelled
MATLAB, no fake `.slx` is shipped, and the UI reports unvalidated reference fallback.

With licensed MATLAB + Simulink installed:

```bash
python scripts/validate_matlab.py
```

Set `MATLAB_EXECUTABLE` if needed. The script calls `matlab/run_validation.m`, builds
two genuine `.slx` models (water-energy coupling and traffic signal response), runs
forecasting and constrained scheduling/intervention search, then compares real
outputs with Python at absolute tolerance **1e-6**. Successful artifacts are used
as offline parity evidence by the app. See [MATLAB integration](docs/matlab-integration.md).

**SUMO 1.27.1 was actually run via TraCI** on the synthetic graph. To reproduce:

```bash
python -m pip install -r requirements-sumo.lock
python scripts/run_sumo.py
```

The interactive optimizer uses the fast numerical traffic model; SUMO is a separate
microscopic experiment. Its measured result is not presented as calibration or a
guaranteed traffic improvement. See [evaluation](docs/evaluation.md) and [SUMO](sumo/README.md).

## Tests and measured evidence

```bash
python -m pytest -q
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
cd ..
python scripts/evaluate.py
python scripts/benchmark.py
```

The tests cover deterministic state, conservation, forecasts, routing, budget
extrema, minimum selection, no-feasible handling, outages, API/database persistence,
stale and concurrent approvals, load repayment, immutable snapshots and browser
approval/safe-failure/mobile/map-input flows. The PostgreSQL test needs a dedicated
`TEST_POSTGRES_URL`; SUMO tests skip visibly if its optional runtime is absent.
Checked-in measured summaries are in [docs/evidence](docs/evidence).

## Architecture and assumptions

FastAPI/Pydantic/SQLAlchemy modular monolith + React/TypeScript/Vite, Leaflet and
ECharts. SQLite for lightweight local operation, PostgreSQL in Compose. A single
canonical UrbanState passes through pure numerical models and a transactional
approval service. No LLM participates in optimization or numerical results.

The first optimization problem is waste collection. Traffic, water and energy
provide coupled dynamics, predictions, safety constraints and executable what-if
actions. It is not a general city optimizer. Minimum vehicle count precedes soft
cost/time/traffic/emissions weights. Other feasible plans remain inspectable.

Model coefficients, road capacities and EV/grid factors are assumptions. Overflow
probabilities are analytical sensitivity to assumed normally distributed fill
rates, not field-calibrated probabilities. Cross-service budgets gate the worst
minute-aligned increase; report averages separately. Five-minute demand forecasts
are labelled separately from the waste risk horizon. Deferred flexible energy is
repaid in an explicit two-hour window. No safe action is a valid result.

The prototype is trusted-local: operator names are audit labels, not authentication.
There are no real actuators or citizen identifiers. Missing domain data fails closed
with a visible error. A real pilot requires measured inputs, model calibration,
authentication/authorization, operational controls and field review.

Our prototype's distinctive contribution is the combination of minimum-effective
intervention search, explicit cross-domain impact budgets, counterfactual Urban
Ripple analysis, and human approval within a modular four-domain ward-level platform.

## Project guide and disclosure

- [Architecture](docs/architecture.md), [state contract](docs/urban-state.md), [domain models](docs/domain-models.md)
- [Optimization](docs/optimization.md), [ripple](docs/urban-ripple.md), [impact budget](docs/impact-budget.md)
- [Stress tests](docs/stress-tests.md), [API](docs/api.md), [demo story](docs/demo.md)
- [Data provenance](docs/data-provenance.md), [ethics and safety](docs/ethics.md), [evaluation](docs/evaluation.md)
- [Implementation plan](implementation-plan.md), [execution record](docs/progress.md)

OpenAI Codex assisted with architecture, implementation, tests and documentation.
MATLAB Copilot and Simulink Copilot were **not** used; no course completion is claimed.
Third-party tools: FastAPI, Pydantic, SQLAlchemy, psycopg, PostgreSQL, React, Vite,
TypeScript, Leaflet, Apache ECharts, Lucide, pytest, Playwright, Docker, Eclipse SUMO,
MATLAB/Simulink (licensed runtime required). No external operational dataset is used.
Optional Google Fonts improve typography; local sans-serif fallbacks remain usable.
