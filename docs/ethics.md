# Safety and deployment boundary

This is human-operated decision support for a simulated ward. It has no real
signals, valves, pumps or grid-control credentials. It requires no citizen PII.
Source, assumptions, model versions, uncertainty, constraints and approval are
recorded in each passport. Low-confidence forecasts and external-runtime fallback
are visible. No safe feasible candidate means no passport and no action.

The primary optimizer minimizes vehicle count before weighted preferences.
Statistical risk is based on an assumed rate distribution, not field calibration.
Per-zone synthetic forecast errors are measured; they do not demonstrate equitable
performance in real neighbourhoods. A pilot needs measured data, engineering
calibration, capacity checks and local operational review before any real action.

The application is intentionally a trusted-local single-operator prototype.
Operator names are audit labels, not authenticated identities. No authentication,
authorization, rate limiting, tamper-proof audit log or retention policy is
implemented. Run on loopback (the default, including Compose); do not expose it as
a public municipal service. SQLAlchemy parameterizes DB writes, Pydantic rejects
invalid/nonfinite measurements, map labels use text nodes, and no secrets are kept.
Audit records are application-level history, not an immutable compliance ledger.

Missing required domain data is rejected with HTTP 422 and never treated as safe.
The prior valid state remains active; the client displays the ingestion error.
