# Minimum effective intervention

For the primary waste problem, enumerate simple depot-to-zone graph routes and
one/two-vehicle alternatives, plus no-op and supported combined controls.
Simulate every action for the identical horizon and seed. Reject any hard-budget
or physical violation before ranking. Minimize number of vehicles first; then
normalized weighted cost, response time, traffic increase and emissions proxy.
The zero-action option is eligible only if it actually achieves the target.
Decision Arena reports feasible winners for response, traffic and cost objectives,
deduplicating identical plans. It never promises three distinct feasible plans.
Energy and water recommendations enumerate discrete flexible-load and pump
adjustments; traffic enumerates bounded green-time changes. The principal demo
optimizes waste, with other domains providing coupled effects and constraints.
