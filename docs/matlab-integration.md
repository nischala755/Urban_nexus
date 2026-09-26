# MATLAB integration contract

`python scripts/validate_matlab.py` discovers MATLAB (or MATLAB_EXECUTABLE), exports
a JSON input fixture, calls MATLAB with `-batch`, and checks its output against
Python references. It runs forecasting, discrete constrained energy scheduling,
minimum-intervention selection, and Simulink water/energy and traffic models.
No Optimization Toolbox is needed: the bounded search is exhaustive enumeration.
JSON includes schema/model versions, input fingerprint, producer, runtime version
and actual output arrays. Python accepts only matching versions and finite values
that meet documented absolute tolerance (1e-6 for deterministic models).
No artifact means unvalidated fallback, shown in the UI. A successful artifact is
used as a validation record for the same equations; it is never treated as live
sensor data. MATLAB/Simulink licenses and installation cannot be replaced by code.
Reference: https://www.mathworks.com/help/simulink/programmatic-modeling.html
