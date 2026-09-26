export type KPI = Record<string, number>
export interface Zone {
  id: string; name: string; x: number; y: number;
  traffic: { delay_seconds: number; density: number; queue_vehicles: number; average_speed_kph: number }
  energy: { demand_kw: number; capacity_kw: number; renewable_kw: number }
  water: { demand_m3h: number; reservoir_m3: number; capacity_m3: number; pump_kw: number }
  waste: { fill_pct: number; rate_pct_h: number }
}
export interface Ward {
  id: string; timestamp: string; elapsed_minutes: number; zones: Zone[]; available_vehicles: number;
  metadata: { seed: number; scenario: string; source_type: string }
}
export interface StateResponse { state: Ward; version: number; kpis: KPI }
export interface Health { status: string; capabilities: { matlab_simulink: string; traffic: string; sumo: string; degraded: boolean } }
export interface Road { a: string; b: string; km: number; capacity_vpm: number; zone: string }
export interface Forecast { predicted: number; method: string; validation_mae: number; interval: number[]; low_confidence: boolean }
export interface Prediction { zone_id: string; energy: Forecast; water: Forecast; traffic: Forecast; waste_overflow_probability: number; water_anomaly_score: number; alerts: { domain: string; message: string }[]; forecast_horizon_minutes: number; waste_horizon_minutes: number }
export interface Action { id: string; label: string; kind: string; zone_id: string; route: string[]; vehicles: number; load_shift_kw: number; pump_adjustment_m3h: number; green_delta_seconds: number }
export interface Constraint { name: string; actual: number; allowed: number; unit: string; margin: number; status: string; minimum: boolean }
export interface Evaluation {
  action: Action;
  simulation: { kpis: KPI; series: KPI[]; affected_zones: string[]; uncertainty: { kind: string; fill_90pct_interval: number[]; low_confidence: boolean } };
  budget: { passed: boolean; constraints: Constraint[] };
  ripple: { deltas: KPI; contributions: { cause: string; effect: string; value: number; unit: string }[] };
  objective: { value: number; contributions: Record<string, number> }
}
export interface Passport {
  id: string; timestamp: string; problem: string; approval_status: string;
  proposed_intervention: Action; model_versions: Record<string, string>; assumptions: string[];
  simulation_seed: number; input_state_id: string; input_state_version: number;
  predicted_kpi: KPI; baseline_kpi: KPI; prediction_uncertainty: { kind: string; fill_90pct_interval: number[] };
  constraint_results: { passed: boolean; constraints: Constraint[] };
  reversibility: string; outcome?: { kpis: KPI; measurement_type: string }
}
export interface Decision {
  status: string; selected: Evaluation | null; baseline: { kpis: KPI; series: KPI[] };
  evaluations: Evaluation[]; alternatives: { action_id: string; objectives: string[] }[];
  feasible_count: number; rejection_summary: Record<string, number>; passport: Passport | null;
}
export interface Stress {
  trajectory: KPI[]; affected_services: string[]; time_to_degradation_minutes: number | null;
  recovery_estimate_minutes: number | null; recovery_note: string
}
