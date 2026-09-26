# Impact budget and gate

Hard limits: traffic delay percentage increase, electricity demand percentage
increase, minimum reservoir %, maximum overflow probability, incremental INR
operating cost, kgCO2e emissions proxy, vehicle capacity/availability, route duration,
signal bounds and feeder capacity. Check reservoir and feeder extrema throughout
the trajectory. Risk must be strictly below the target. Other upper/lower bounds
are inclusive. Return actual, allowed, unit, margin and PASS/FAIL for every check.
Zero baselines use an explicit small denominator for percentage comparisons.
Budgets and soft weights are validated finite nonnegative values.
No feasible action returns NO SAFE ACTION FOUND and actionable failed constraints.
Human approval never relaxes a limit. Changed settings require a new evaluation.
