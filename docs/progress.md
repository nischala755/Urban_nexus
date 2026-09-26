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
