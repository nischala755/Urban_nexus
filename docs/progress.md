# Execution ledger — implementation-plan.md

Pre-flight: shared interfaces are UrbanState -> numerical simulation -> decision ->
passport persistence -> API -> UI. All use Pydantic JSON with finite numeric values.
Ruling: implement in the supplied empty workspace on a feature branch; no existing
work needs worktree isolation. Cost if wrong: work can be moved with git later.
Ruling: SQLite local plus PostgreSQL Compose avoids requiring Docker to demonstrate
the core idea. Cost if wrong: PostgreSQL-specific behavior needs its own CI run.
Ruling: continue ordinary design decisions without review pauses as expressly
requested. Written architecture and plan remain available for review.
Environment: Python 3.12 and Node 24 available; Docker CLI exists but daemon is off;
MATLAB and SUMO not found on PATH or in standard Program Files directories.

Task 1: complete — seven tests pass for generation, validation and persistence.
Task 2 numerical models: complete — six additional domain tests pass.
Task 3: complete — 20 tests pass across state, domain and decision safety contracts.
The synthetic graph has one constrained corridor and two higher-capacity
alternatives. Capacities are illustrative inputs, not fitted city data.
Arena objectives may agree; additional feasible plans use actual weighted rank.

Task 4: complete — API approval/reject/restart/stale/replay tests pass.
Task 5: browser flow verified — stress/approval, no-safe-action, mobile layout,
and untrusted map-label text all pass. Map labels now use DOM textContent.
External runtime: SUMO 1.27.1 actually executed two synthetic scenarios via TraCI,
300/301 completed trips. MATLAB validation script explicitly exits unavailable.
Independent review confirmed six model/audit findings. Regression tests failed
first, then passed: canonical immutable ingest IDs, peak paired-series budgets,
full route completion within horizon, explicit deferred-energy repayment,
fixed five-minute forecast labelling, and rejection of unsupported signal cycles.

Task 6: local verification — 38 backend tests passed, 1 PostgreSQL test skipped
in the default local suite; real SUMO test included. Four Playwright tests passed.
PostgreSQL was then verified separately inside the built Docker Compose app:
two approval/replay/concurrency integration tests passed against PostgreSQL 16. Both services
healthy, served on 127.0.0.1:8000. Docker is no longer an outstanding requirement.
Measured reports copied to docs/evidence, including honest MATLAB unavailable status.
MATLAB/Simulink actual execution remains an environmental dependency, not completed.

Final integration decision: keep the new feature branch in the supplied workspace;
there is no prior base branch or remote to merge/publish. This follows the request
to make ordinary engineering decisions without confirmation. No remote push made.
No minor review findings were deferred. External validation remains explicitly open.

Final concurrency regression: repeated suite exposed two same-outcome inserts
racing before the version gate. A barrier now reproduces simultaneous evaluation;
revision reservation is performed before snapshot insertion in one transaction.
The losing request returns 409, and only one state revision/action commits.
Final rebuilt Docker verification: both PostgreSQL tests passed (2.23 seconds),
and all four Playwright workflows passed against the live Compose app (44.7 seconds).
The full demo, including actual SUMO execution, was regenerated successfully.
