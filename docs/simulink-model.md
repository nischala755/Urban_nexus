# Simulink prototypes

Programmatic builders create genuine .slx models using built-in Simulink blocks.
Water model: demand input, volume feedback, proportional refill control, saturation,
discrete mass balance and pump electricity output. A demand step demonstrates the
water-to-energy relationship. Traffic model: arrivals minus signal service, a
nonnegative discrete queue integrator and derived delay. Both use fixed steps and
workspace logging. Generated models/results are only claimed after MATLAB runs.
`matlab/run_validation.m` builds, saves, simulates and exports these models.
Python reference results are a fallback, never labelled as Simulink output.
