# Measured prototype evaluation

Measurements below were actually produced on this development machine. They are
synthetic prototype results, not municipal improvements or field accuracy claims.
Machine-readable reports live in `docs/evidence/`; regenerate with the scripts.

## End-to-end numerical demo

Seed 42, combined peak-hour stress, all four zones, 60-minute horizon, target Z04:

| Item | Computed result |
|---|---:|
| No-action overflow probability | 89.7996% |
| Selected action | One EV via DEPOT → Z02 → Z04 |
| Modelled post-action probability | Below 0.1% (floating-point tail rounds to zero) |
| Maximum minute-aligned traffic delay increase | 0.56044% |
| Maximum minute-aligned electricity demand increase | 0.49133% |
| Minimum reservoir level across trajectory | 60.4014% |
| Estimated operational cost | INR 1,367.95 |
| Collection travel + service duration | 42.369 minutes |
| Illustrative emissions proxy | 8.63746 kgCO2e |
| Feasible plans / evaluated plans | 2 / 7 |

These values are computed, not hardcoded outputs. Road capacities and model
coefficients are intentionally authored synthetic inputs. The assumed uncertain
fill rate makes a timely collection's tail probability extremely small; the UI
uses `<0.1%` rather than implying a field guarantee of zero risk.

All hard constraints pass for the selected action. A zero traffic-impact budget
produces **NO SAFE ACTION FOUND** and no passport. The automated demo records an
explicitly labelled acceptance-test operator; the UI requires a person to approve.
Approval is transactional and repeat/stale/concurrent attempts cannot apply twice.

## Forecast and anomaly evaluation

`scripts/evaluate.py`: seed 20260926, 100 independently generated held-out cases per
zone and domain. Twelve history points select persistence or short linear trend
using rolling-origin MAE; the next unseen sample provides the external error.
Models are compared without fitting to that unseen point. Reported metrics include
MAE, RMSE and per-zone anomaly precision, recall and F1 on labelled 50% surges.

The selected predictor's errors are close to persistence; it is not uniformly
better across zones. For example, energy Z04 MAE is 6.372 kW versus persistence
6.779 kW; energy Z03 is 7.049 versus 7.033 kW. Water Z03 is 2.211 versus 2.124 m3/h.
These counterexamples are retained in the evidence, not omitted. The selection
policy uses prior rolling validation, not future test labels. No real-world
accuracy, leak localization or equitable-performance claim follows from these data.

## Benchmarks

Windows 11, Python 3.12.10; ten samples, in-process FastAPI TestClient with SQLite
in memory. Includes database operations/serialization, excludes network transport.

| Operation | Median | Maximum | Local target |
|---|---:|---:|---:|
| Current state | 2.13 ms | 3.52 ms | 500 ms |
| Candidate generation | 2.18 ms | 2.42 ms | 2,000 ms |
| Minimum-intervention search | 58.75 ms | 64.64 ms | 5,000 ms |
| Stress test | 28.21 ms | 31.53 ms | 10,000 ms |

These are a measured run, not throughput/load/SLA guarantees. Rerun for your machine.

## Real SUMO/TraCI run

SUMO 1.27.1, seed 42, same synthetic five-node graph with documented lane assumptions:
300 background trips without collection, 301 total with the EV collection vehicle;
all completed. Baseline background delay averaged 110.504 seconds, action-world
110.012 seconds; maximum sampled queue changed from 0 to 3 vehicles. The microscopic
delay difference was **-0.492 seconds**, not the fluid model's positive estimate.
Different vehicle interactions/random draw consumption can change its sign.

This confirms a working microscopic integration and exposes model disagreement.
It does **not** calibrate the fluid model, prove its precision, or establish that
collection improves traffic. Both raw tripinfo XML files are reproducible under
`artifacts/sumo/`. The application explicitly names the fluid model as its runtime.

## Verification and remaining external requirement

Backend tests cover schemas, equations, conservation, uncertainty, minimum search,
hard constraints, intermediate extrema, API, persistence, concurrent approval,
snapshot immutability, load repayment and real SUMO execution. Browser tests cover
stress-to-approval, safe failure, mobile width and untrusted map-label input. Build,
lint and dependency checks are run locally. Exact counts are in the execution record.
Docker Compose was built and started against PostgreSQL 16, with healthy app/database
services; the PostgreSQL approval/replay test passed inside the container. The local
default suite reports that optional test skipped when no TEST_POSTGRES_URL is set;
its separate container run is recorded, rather than pretending that skip was a pass.

**MATLAB/Simulink remain unexecuted.** The validation command exits 2 with an explicit
unavailable report. Executable MATLAB functions and Simulink builders are present,
but the mandatory real MATLAB result, generated `.slx` models and cross-runtime
parity remain outstanding until a licensed installation runs the command. Reference
equations are tested in Python; calling them MATLAB-validated would be incorrect.
