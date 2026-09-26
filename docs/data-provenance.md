# Data provenance

Every operational reading is synthetic. There is no Bengaluru municipal feed,
private dataset, IoT connection, citizen PII, or external actuator credential.
The representative ward's four schematic coordinates and road lengths/capacities
are explicitly authored assumptions in `generator.py` and `network.py`.

`ward-generator/1.0` uses Python's local seeded random generator, a fixed synthetic
UTC start of 2026-01-01 07:50, and a content-derived state ID. The demo seed is 42.
State provenance stores source_type, generator_version, seed, scenario, assumptions;
the UrbanState timestamp describes simulated time, not collection from sensors.
Passports separately record actual generation/approval timestamps.

Validation data uses seed 20260926, independently generated linear drift plus
Gaussian measurement noise, with labelled 50% surges for detection evaluation.
Actual errors are saved to artifacts/evaluation.json. This is evidence about
synthetic cases only, not real-world forecasting accuracy or fairness guarantees.
SUMO output is labelled SUMO/TraCI and includes the executable version and seed.
MATLAB output may only be labelled MATLAB after the licensed tool runs.
