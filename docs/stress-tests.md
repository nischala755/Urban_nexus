# City Stress Test

Supported disturbances: combined peak hour; traffic, water, energy or waste surge;
pump outage; collection vehicle failure. Requests specify scenario, severity
(0.1–3), duration (15–180 minutes), affected zones and seed. Unknown zones fail.
Each run starts a fresh deterministic ward and advances ten minutes before the
disturbance. This intentionally replaces the active simulated scenario with an
audited state revision, making all prior pending passports stale.

Multipliers are transparent: traffic 1+0.55s, water 1+0.60s, energy base 1+0.65s,
waste generation 1+3.7s. Severity does not scale an outage: a selected pump is off;
vehicle failure disables the shared ward collection fleet, regardless of the zone
selection. These are stress inputs, not predicted disaster magnitudes.

Output includes normal, disturbed and projected states, minute traces, affected
services, numerical degradation time and a bounded no-action recovery experiment.
Degradation means reservoir <40%, target bin >=100%, ward mean delay >60 seconds,
or demand >80% of aggregate feeder capacity. These are scenario indicators; the
intervention gate separately applies configurable budgets and all physical limits.
No unassisted recovery within 120 minutes is returned as null/unresolved, not an
invented timestamp. A recommended post-intervention state appears in the decision
result, and an approved outcome is committed to the ward and audit.
