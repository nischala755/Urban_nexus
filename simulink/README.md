# Reproducible model builders

`water_energy/build_water_energy_model.m` builds a bounded discrete reservoir,
proportional pump controller and electricity coupling.
`traffic_control/build_traffic_control_model.m` builds a signal-service fluid queue.
`matlab/run_validation.m` saves real `.slx` files under `artifacts/simulink/`,
simulates both and exports arrays for reference comparison.
Builders are source code, not proof that MATLAB/Simulink executed. No `.slx` is
fabricated when the runtime is absent. See `docs/evaluation.md` for actual status.
