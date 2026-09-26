# Interpretable numerical models

All parameters are illustrative synthetic assumptions, not field calibration.
Traffic uses a fluid queue: q(t+dt)=max(0,q+(arrival-service)*dt), service from
green time/cycle and saturation flow. Route trucks add passenger-car-equivalent
occupancy on the graph edges they traverse. Delay, speed and travel time follow
the queue and saturation; no signal or actuator is connected.

Water integrates volume from pump inflow minus demand. A bounded proportional
controller adds refill flow towards 65% volume. Pump kW = flow * 0.6 kWh/m3.
Energy adds base, flexible and pump loads, subtracts renewables for net grid use.
Flexible scheduling searches allowed one-hour load shifts; deferred energy is
persisted as a kWh debt, normal flexible load resumes at the horizon boundary and
the debt is repaid over 120 minutes across subsequent simulation calls. Recovery
feeder safety conservatively assumes maximum pump power. The controller uses a
fixed 60-second signal cycle; other cycle values are rejected.

Waste fill evolves linearly between collections. A normally distributed uncertain
fill rate provides a model-based probability of crossing 100%, considering both
arrival-before-collection and the remainder of the horizon. It is not a calibrated
real-world probability. Capacity and service-time constraints are explicit.
Prediction intervals are sensitivity to this assumed rate distribution.

Forecasts compare persistence against a short linear trend on held-out synthetic
data; deploy the measured lower-MAE method. Anomaly detection is a robust history
deviation. Report per-zone errors and precision/recall on labelled synthetic surges.
No underground leak localization claim is made.
Service histories represent five-minute samples. Energy, water and traffic
forecasts predict the next sample (five minutes); only waste risk uses the
requested 15–180-minute counterfactual horizon. These are labelled separately.
