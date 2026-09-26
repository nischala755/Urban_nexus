# Microscopic traffic validation

Install `pip install -e ".[sumo]"`, then run `python scripts/run_sumo.py`.
The adapter builds the same five-node ward graph with netconvert, generates seeded
background traffic, runs a no-dispatch baseline and a collection-truck scenario
through TraCI, and measures queue, speed, waiting, travel and time loss. Inputs,
network, tripinfo XML and results are written under `artifacts/sumo/`.

SUMO is a separate microscopic validation experiment, not a calibration claim.
The interactive counterfactual search uses the documented fast fluid-queue model.
The one-command demo includes SUMO validation when the optional runtime is present.
Lane counts are illustrative (one on the constrained corridor, two otherwise),
not inferred from the fluid-model aggregate capacities. The simulator has no real
traffic-signal connection. Seed and executable version are recorded.

Reference: https://eclipse.dev/sumo/docs/TraCI/Interfacing_TraCI_from_Python.html
