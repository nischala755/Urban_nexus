# Peak-Hour Urban Stress

`python scripts/demo.py` runs an isolated reproducible API demo with seed 42.
It creates the normal ward, advances ten minutes, injects combined traffic/water/
energy/waste stress, obtains alerts, enumerates/simulates candidates and applies
the budget. It writes an Action Passport and verifies before/after KPIs.
The automation is a test harness with a clearly named simulated operator approval;
the interactive command center requires the person to click Approve & simulate.
Tightening the traffic budget demonstrates safe failure; no recommendation appears
when every effective action fails a hard constraint. Rejection leaves state intact.
Outputs go to `artifacts/demo.json`, with source labels, seed and model versions.
