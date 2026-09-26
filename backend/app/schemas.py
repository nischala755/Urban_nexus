"""Canonical contracts. Units are part of field names; unknown fields are errors."""
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, validate_assignment=True)


class Traffic(Contract):
    arrival_vpm: Nonnegative
    queue_vehicles: Nonnegative
    green_seconds: Annotated[float, Field(ge=15, le=45)] = 30
    cycle_seconds: Positive = 60
    density: Nonnegative
    vehicle_count: Nonnegative
    average_speed_kph: Nonnegative
    delay_seconds: Nonnegative
    history: list[Nonnegative] = Field(min_length=3, max_length=100)


class Energy(Contract):
    base_kw: Nonnegative
    flexible_kw: Nonnegative
    renewable_kw: Nonnegative
    demand_kw: Nonnegative
    capacity_kw: Positive = 750
    history: list[Nonnegative] = Field(min_length=3, max_length=100)


class Water(Contract):
    demand_m3h: Nonnegative
    reservoir_m3: Nonnegative
    capacity_m3: Positive = 1000
    pump_capacity_m3h: Positive = 300
    pump_flow_m3h: Nonnegative
    pump_kw: Nonnegative
    pump_available: bool = True
    history: list[Nonnegative] = Field(min_length=3, max_length=100)

    @model_validator(mode="after")
    def physical_bounds(self):
        if self.reservoir_m3 > self.capacity_m3 or self.pump_flow_m3h > self.pump_capacity_m3h:
            raise ValueError("Water storage/flow exceeds physical capacity")
        return self


class Waste(Contract):
    fill_pct: Annotated[float, Field(ge=0, le=300)]
    rate_pct_h: Nonnegative
    rate_std_pct_h: Nonnegative
    bin_capacity_m3: Positive = 10


class Zone(Contract):
    id: str = Field(pattern=r"^Z\d{2}$")
    name: str
    x: float
    y: float
    traffic: Traffic
    energy: Energy
    water: Water
    waste: Waste


class Provenance(Contract):
    source_type: Literal["synthetic"] = "synthetic"
    generator_version: str = "ward-generator/1.0"
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)]
    scenario: str = "normal"
    assumptions: list[str] = Field(default_factory=lambda: [
        "Representative four-zone ward; no municipal infrastructure connection",
        "Illustrative parameters; probabilities are not field calibrated",
        "Deterministic one-minute fluid dynamics; EV collection fleet",
    ])


class UrbanState(Contract):
    id: str
    timestamp: datetime
    elapsed_minutes: Nonnegative = 0
    zones: list[Zone] = Field(min_length=1, max_length=20)
    available_vehicles: Annotated[int, Field(ge=0, le=10)] = 2
    vehicle_capacity_m3: Positive = 12
    temperature_c: float = 28
    metadata: Provenance

    @model_validator(mode="after")
    def unique_zones(self):
        if len({z.id for z in self.zones}) != len(self.zones):
            raise ValueError("Zone IDs must be unique")
        if self.timestamp.tzinfo is None:
            raise ValueError("Timestamp must include timezone")
        return self


class Action(Contract):
    id: str
    label: str
    kind: Literal["none", "waste", "energy", "water", "traffic", "combined"] = "none"
    zone_id: str = "Z04"
    route: list[str] = Field(default_factory=list, max_length=8)
    vehicles: Annotated[int, Field(ge=0, le=2)] = 0
    load_shift_kw: Annotated[float, Field(ge=0, le=120)] = 0
    pump_adjustment_m3h: Annotated[float, Field(ge=-100, le=100)] = 0
    green_delta_seconds: Annotated[float, Field(ge=-15, le=15)] = 0


class ImpactBudget(Contract):
    traffic_delay_max_delta: Nonnegative = 3
    energy_demand_max_delta: Nonnegative = 2
    water_reservoir_min: Percent = 40
    waste_overflow_max: Annotated[float, Field(gt=0, le=1)] = 0.10
    cost_max: Nonnegative = 5000
    emissions_proxy_max: Nonnegative = 30
    route_duration_max: Positive = 60


class Weights(Contract):
    cost: Nonnegative = 0.4
    time: Nonnegative = 0.3
    traffic: Nonnegative = 0.2
    emissions: Nonnegative = 0.1

    @model_validator(mode="after")
    def not_all_zero(self):
        if not sum(self.model_dump().values()):
            raise ValueError("At least one objective weight must be positive")
        return self


class DecisionRequest(Contract):
    zone_id: str = "Z04"
    horizon_minutes: Annotated[int, Field(ge=15, le=180)] = 60
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 42
    budget: ImpactBudget = Field(default_factory=ImpactBudget)
    weights: Weights = Field(default_factory=Weights)


class EvaluateRequest(DecisionRequest):
    action: Action


class StressRequest(Contract):
    scenario: Literal["combined", "traffic_surge", "water_surge", "energy_peak",
                      "waste_surge", "pump_outage", "vehicle_failure"] = "combined"
    severity: Annotated[float, Field(ge=0.1, le=3)] = 1
    duration_minutes: Annotated[int, Field(ge=15, le=180)] = 60
    affected_zones: list[str] = Field(default_factory=lambda: ["Z01", "Z02", "Z03", "Z04"],
                                      min_length=1, max_length=20)
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 42


class Approval(Contract):
    operator: str = Field(min_length=1, max_length=100, pattern=r".*\S.*")
    note: str = Field(default="", max_length=1000)


class ResetRequest(Contract):
    seed: Annotated[int, Field(ge=0, le=2**31 - 1)] = 42
