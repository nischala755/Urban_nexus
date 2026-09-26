# Urban Ripple

Each edge has units, formula, assumptions and synthetic-model provenance:
water flow -> pump electricity: m3/h * 0.6 kWh/m3 = kW;
collection -> traffic: truck PCU / road capacity -> changed queue/delay;
distance and delay -> EV energy: km * kWh/km + idle minutes * kWh/min;
grid electricity -> emissions proxy: kWh * assumed kgCO2e/kWh.
Report causal contributions separately from measured aggregate KPI deltas.
The baseline is a no-action projection with the same exogenous disturbance.
Waste collections do not invent a water impact; shared water demand and pump
operation still evolve in both worlds. Simulink validates water/energy equations
through an offline result contract when the licensed runtime is available.
