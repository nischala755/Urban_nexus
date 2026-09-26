# API

Start the app, then open `/docs` for generated OpenAPI and executable request forms.
All operational routes use `/api/v1`; `/health` reports source and actual backends.

GET: state/current, zones, predictions, alerts, action-passports,
action-passports/{id}, kpis/baseline, kpis/comparison, audit.

POST: state/ingest (validated synthetic UrbanState), state/reset ({seed}),
stress-tests/run (scenario, severity, duration_minutes, affected_zones, seed),
interventions/candidates, interventions/evaluate, interventions/minimum-effective,
what-if/simulate, ripple/evaluate, impact-budget/check,
action-passports/{id}/approve and /reject ({operator, note}).

Decision requests share zone_id, horizon_minutes, seed, budget and weights.
Evaluation/what-if adds an Action. Candidate actions are returned by the server;
unknown road edges or zones fail 422. Numerical/domain what-if returns a complete
counterfactual, constraints and ripple but does not change state or approve it.
Minimum search persists a pending passport only when feasible. Approval reruns
the same input/action/seed/budget, verifies state revision, then atomically commits
outcome, status and audit. HTTP 409 indicates stale/replayed/concurrent action;
404 means unknown passport; 422 means invalid input.

`kpis/baseline` is a 60-minute no-action projection of current state.
`kpis/comparison` is the most recently approved passport's paired numerical worlds,
even if a later stress test resets the active scenario; its action_id identifies
which experiment it belongs to. No field observation is implied.
