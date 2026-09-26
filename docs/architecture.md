# UrbanNexus prototype design

## Intent and scope
Prove one complete ward-level decision: detect waste overflow under peak-hour
stress, enumerate collection routes, simulate all four services, reject collateral
budget violations, select the least resource-intensive feasible action, issue a
passport, record a human decision and simulate the resulting state. Four synthetic
zones share a depot and an explicit road graph. No municipal systems are connected.

## Decisions and alternatives
A modular FastAPI monolith with React/TypeScript is the chosen implementation.
It keeps one state contract and a single transaction boundary for approval.
A notebook-only demo would omit the operator workflow; microservices would add
failure modes without helping this one-ward experiment. SQLite is the zero-service
local default; Docker Compose uses PostgreSQL through the same SQLAlchemy schema.
PostGIS is unnecessary for the tiny synthetic graph. Leaflet uses a local schematic
coordinate system without map tiles; ECharts plots actual simulation time series.

## Boundaries
`backend/app/schemas.py`: canonical Pydantic contracts and validation.
`generator.py`: repeatable synthetic state and provenance.
`domains.py`: traffic, water, energy, waste equations and forecasts.
`simulation.py`: pure counterfactual evolution and explicit ripple contributions.
`decision.py`: candidate enumeration, budget gate, lexicographic selection.
`stress.py`: disturbances, degradation and recovery simulation.
`db.py` / `service.py`: state snapshots, passports, audit and atomic approval.
`main.py`: versioned API and optional built frontend serving.
`integrations.py`: visible capability status and verified offline model imports.
`matlab/` and `simulink/`: reproducible MATLAB functions and model builders.

## Safety and persistence
Counterfactuals never mutate their input. Compare actions to a no-action projection
at the same horizon, not to a different time. Store both initial and projected
baseline. Minimum magnitude is lexicographic before weighted soft objectives.
Approval checks the current state version, re-evaluates constraints and commits
passport status, simulated outcome, state pointer and audit event atomically.
Repeated approval cannot apply an action twice. Rejected/stale actions cannot act.
No safe candidate means an explicit empty recommendation, with rejection reasons.

## Environment assumptions
This is a trusted-local, single-operator hackathon app, not an authenticated service.
Licensed MATLAB/Simulink and SUMO are optional at application runtime, but actual
MATLAB/Simulink validation remains a submission requirement. Missing executables
must be reported; authored scripts alone are not evidence of execution.
The empty user-selected workspace is initialized in place on a feature branch.

## Success checks
Seed repeatability; unit consistency; reservoir mass balance; monotonic risk;
route/capacity rejection; exact smallest feasible search; no feasible path;
approval replay and stale-state rejection; SQLite and PostgreSQL contracts;
API/UI stress-to-passport-to-outcome flow; numerical cross-runtime parity when
licensed tools exist; measured benchmarks and honest validation reports.
