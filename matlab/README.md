# MATLAB prototypes

Run `python scripts/validate_matlab.py` from the repository root with MATLAB and
Simulink licensed. This executes rolling-origin forecast selection, constrained
one-hour load placement and lexicographic minimum-intervention enumeration, then
builds and simulates the two real Simulink models. No Optimization Toolbox needed.
Result JSON is checked by Python at absolute tolerance 1e-6. Actual successful
output is loaded by `/health` as parity evidence for the application's equations.
Until that succeeds, the UI explicitly reports unvalidated Python fallback.
MATLAB Copilot and Simulink Copilot were not used.
